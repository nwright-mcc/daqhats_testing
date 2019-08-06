#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <signal.h>
#include <fcntl.h>
#include <time.h>
#include <syslog.h>
#include <daqhats/daqhats.h>

#define MIN_BOARD       0
#define NUM_BOARDS      4

#define NUM_CHANNELS    2
#define CHAN_MASK       0x03

const double rates[4] =
{
    51200.0,
    51200.0,
    51200.0,
    12800.0
};

#define LOG_DATA	

#define buffer_size	1000000

static volatile int keepRunning = 1;
void intHandler(int dummy)
{
    keepRunning = 0;
}

int main(int argc, char* argv[])
{
    uint16_t address;
    char buffer[256];
    int fd;
    int error;
    bool scan_running;
    uint16_t samples;
    int i;
    char time_str[16];
    struct tm* my_time;
    time_t time_now;
    char msg[256];
    uint16_t options;
    uint16_t flags;
    FILE* log_files[NUM_BOARDS];
    double temp_buffer[buffer_size];
    uint32_t scans_read;
    uint32_t min_read, max_read;
    double read_rate;
    uint16_t index;
    uint16_t status;



    signal(SIGINT, intHandler);

    for (i = MIN_BOARD; i < (MIN_BOARD+NUM_BOARDS); i++)
    {
#ifdef LOG_DATA
        sprintf(msg, "./log%d.bin", i);
        if ((log_files[i] = fopen(msg, "wb")) == NULL)
        {
            printf("Can't open log file.\n");
            return 1;
        }
#endif
        if (mcc172_open(i) != RESULT_SUCCESS)
        {
            printf("Can't open device.\n");
            return 1;
        }

        mcc172_a_in_clock_config_write(i, SOURCE_LOCAL, rates[i]);
    }

    openlog("scan_test", LOG_ODELAY, LOG_USER);
    syslog(LOG_INFO, "Start");

    options = OPTS_CONTINUOUS; // | OPTS_NOCALIBRATEDATA | OPTS_NOSCALEDATA;

    for (i = MIN_BOARD; i < (MIN_BOARD+NUM_BOARDS); i++)
    {
        if ((error = mcc172_a_in_scan_start(i, CHAN_MASK, buffer_size, options))
            != RESULT_SUCCESS)
        {
            printf("Can't start scan %d %d.\n", i, error);
            mcc172_close(i);
            syslog(LOG_NOTICE, "Can't start scan");
            syslog(LOG_INFO, "Stop");
            closelog();
            return 1;
        }
    }

    time_now = time(NULL);
    my_time = localtime(&time_now);
    strftime(time_str, 16, "%T", my_time);
    printf("Start %s\n", time_str);

    uint32_t total_read = 0;
    struct timespec start_time;
    struct timespec current_time;

    clock_gettime(CLOCK_MONOTONIC, &start_time);
    double start_t = (start_time.tv_sec + start_time.tv_nsec*1e-9);

    setbuf(stdout, NULL);
    min_read = 0xFFFFFFFF;
    max_read = 0;
    while (keepRunning)
    {
        for (i = MIN_BOARD; i < (MIN_BOARD+NUM_BOARDS); i++)
        {
            // Read as much data as possible from each board
            mcc172_a_in_scan_read(i, &status, buffer_size, 0.1, temp_buffer, buffer_size, &scans_read);
            total_read += (scans_read * NUM_CHANNELS);

            if (i == MIN_BOARD)
            {
                clock_gettime(CLOCK_MONOTONIC, &current_time);

                read_rate = total_read / ((current_time.tv_sec + current_time.tv_nsec*1e-9) - start_t);
                printf("%d %10.2f\r", total_read, read_rate);
            }

            if (scans_read > max_read)
            {
                max_read = scans_read;
            }
            if ((scans_read > 0) && (scans_read < min_read))
            {
                min_read = scans_read;
            }

            if ((status & (STATUS_HW_OVERRUN | STATUS_BUFFER_OVERRUN)) != 0)
            {
                // an error occurred
                printf("Overrun %d %02X          \n", i, status);
                keepRunning = false;
                break;
            }
#ifdef LOG_DATA
            fwrite(temp_buffer, scans_read*sizeof(double), 1, log_files[i]);
#endif
        }
    }

    for (i = MIN_BOARD; i < (MIN_BOARD+NUM_BOARDS); i++)
    {
        mcc172_a_in_scan_stop(i);
        mcc172_a_in_scan_cleanup(i);
        mcc172_close(i);
#ifdef LOG_DATA
        fclose(log_files[i]);
#endif
    }

    printf("min: %u max:%u\n", min_read, max_read);
    syslog(LOG_INFO, "Stop");
    closelog();
    return 0;
}
