#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <daqhats/daqhats.h>

const char* default_filename = "./test.csv";


int read_args(int argc, char **argv, uint8_t* address, uint8_t* iepe_on,
    double* sample_rate_per_channel, uint32_t* samples, char* filename, uint8_t* slave,
    uint8_t* master)
{
    int c;

    opterr = 0;

    while ((c = getopt(argc, argv, "msha:f:n:o:i:")) != -1)
    {
        switch (c)
        {
        case 'a':
            *address = atoi(optarg);
            break;
        case 'f':
            *sample_rate_per_channel = atof(optarg);
            break;
        case 'n':
            *samples = strtoul(optarg, NULL, 10);
            break;
        case 'i':
            *iepe_on = atoi(optarg);
            break;
        case 'h':
            return 1;
            break;
        case 'm':
            *master = 1;
            break;
        case 's':
            // slave device
            *slave = 1;
            break;
        case 'o':
            strcpy(filename, optarg);
            break;
        case '?':
            if ((optopt == 'a') || (optopt == 'f') || (optopt == 'i') ||
                (optopt == 'n') || (optopt == 'o'))
                fprintf (stderr, "Option -%c requires an argument.\n", optopt);
            else if (isprint (optopt))
                fprintf (stderr, "Unknown option `-%c'.\n", optopt);
            else
                fprintf (stderr,  "Unknown option character `\\x%x'.\n", optopt);
            return 1;
        default:
            abort ();
        }
    }

    if (*master && *slave)
    {
        fprintf(stderr, "Options -m and -s are mutually exclusive.\n");
        return 1;
    }
    return 0;
}

int main(int argc, char* argv[])
{
    uint32_t samples_per_channel;
    uint32_t samples_read_per_channel;
    int num_channels;
    uint8_t address;
    uint8_t channels;
    uint8_t options;
    uint8_t slave;
    uint8_t master;
    uint16_t status;
    double* data;
    double sample_rate_per_channel;
    double adc_clock;
    FILE* logfile;
    int index;
    int result;
    uint8_t clock_source;
    char filename[256];
    uint8_t synced;
    uint8_t iepe_on;

    sample_rate_per_channel = 51200.0;
    samples_per_channel = 25600*1;
    address = 0;
    iepe_on = 0;
    slave = 0;
    master = 0;
    strcpy(filename, default_filename);

    if (read_args(argc, argv, &address, &iepe_on, &sample_rate_per_channel,
        &samples_per_channel, filename, &slave, &master) != 0)
    {
        fprintf(stderr,
            "Usage: %s [-a address] [-s] [-m] [-f frequency] [-n samples] [-i iepe] [-o file]\n"
            "    -a address: address [0-7] of the HAT to scan (default is 0)\n"
            "    -s : device is a clock slave\n"
            "    -m : device is a clock master\n"
            "    -f frequency: ADC sampling frequency (default is 51200)\n"
            "    -n samples: number of samples (default is 51200)\n"
            "    -i iepe: IEPE power off (0) or on (1) (default is off)\n"
            "    -o file: output file name (default is ./test.csv)\n",
            argv[0]);
        return 1;
    }

    channels = 0x03;
    num_channels = 2;
    options = /*OPTS_NOSCALEDATA |*/ OPTS_NOCALIBRATEDATA;

    result = mcc172_open(address);
    if (result != RESULT_SUCCESS)
    {
        printf("open returned %d\n", result);
        return 1;
    }

#if 0
    result = mcc172_blink_led(address, 10);
    if (result != RESULT_SUCCESS)
    {
        printf("blink returned %d\n", result);
        mcc172_close(address);
        return 1;
    }

    mcc172_close(address);
    return 0;
#endif

    result = mcc172_a_in_scan_stop(address);
    if (result != RESULT_SUCCESS)
    {
        printf("scan_stop returned %d\n", result);
        mcc172_close(address);
        return 1;
    }

    // configure IEPE
    if (iepe_on != 0)
    {
        iepe_on = 1;
    }

    result = mcc172_iepe_config_write(address, 0, iepe_on);
    if (result != RESULT_SUCCESS)
    {
        printf("iepe_config returned %d\n", result);
        mcc172_close(address);
        return 1;
    }
    result = mcc172_iepe_config_write(address, 1, iepe_on);
    if (result != RESULT_SUCCESS)
    {
        printf("iepe_config returned %d\n", result);
        mcc172_close(address);
        return 1;
    }
    printf("IEPE power %s\n", iepe_on == 0 ? "off" : "on");

#if 1
    // configure ADC clock

    if (master)
    {
        clock_source = SOURCE_MASTER;
    }
    else if (slave)
    {
        clock_source = SOURCE_SLAVE;
    }
    else
    {
        clock_source = SOURCE_LOCAL;   // local mode
    }

    result = mcc172_a_in_clock_config_write(address, clock_source, sample_rate_per_channel);
    if (result != RESULT_SUCCESS)
    {
        printf("clock_config returned %d\n", result);
        mcc172_close(address);
        return 1;
    }

    do
    {
        usleep(1000);
        result = mcc172_a_in_clock_config_read(address, &clock_source, &adc_clock, &synced);
        if (result != RESULT_SUCCESS)
        {
            printf("clock_config_read returned %d\n", result);
            mcc172_close(address);
            return 1;
        }
    } while (synced == 0);
    printf("ADC clock set to %.1f Hz\n", adc_clock);
#endif

#if 0
    result = mcc172_a_in_decimate_factor_write(address, (int)(51200/sample_rate_per_channel));
    if (result != RESULT_SUCCESS)
    {
        printf("decimate_factor returned %d\n", result);
        mcc172_close(address);
        return 1;
    }
    printf("Decimate factor set to %d\n", (int)(51200/sample_rate_per_channel));
#endif

    printf("Scanning %d samples...\n", samples_per_channel);
    result = mcc172_a_in_scan_start(address, channels, samples_per_channel, options);
    if (result != RESULT_SUCCESS)
    {
        printf("scan_start returned %d\n", result);
        mcc172_close(address);
        return 1;
    }

    int buffer_size_samples = samples_per_channel * num_channels;
    data = (double*)malloc(buffer_size_samples * sizeof(double));
    double* ptr = data;
    uint32_t samples_read = 0;

    //printf("Read: 0\n");
    // wait for scan to complete
    do
    {
        result = mcc172_a_in_scan_read(address, &status, -1, 0.0, ptr,
            buffer_size_samples - samples_read, &samples_read_per_channel);
        samples_read += num_channels * samples_read_per_channel;
        ptr += samples_read_per_channel * num_channels;
        if (samples_read_per_channel > 0)
        {
            //printf("Read: %d %X %d %d\n", result, status, samples_read_per_channel, samples_read);
        }
        usleep(5000);
    } while ((result == RESULT_SUCCESS) && ((status & STATUS_RUNNING) == STATUS_RUNNING));

    if (result != RESULT_SUCCESS)
    {
        printf("\nscan_read returned %d\n", result);
    }
    else
    {
        printf("\nComplete\n");
    }

    result = mcc172_a_in_scan_cleanup(address);
    if (result != RESULT_SUCCESS)
    {
        printf("scan_cleanup returned %d\n", result);
        mcc172_a_in_scan_stop(address);
        mcc172_close(address);
        free(data);
        return 1;
    }

    result = mcc172_close(address);
    if (result != RESULT_SUCCESS)
    {
        printf("close returned %d\n", result);
    }

    logfile = fopen(filename, "wt");
    for (index = 0; index < samples_read/num_channels; index++)
    {
        for (int channel = 0; channel < num_channels; channel++)
        {
            fprintf(logfile, "%f,", data[(index * num_channels) + channel]);
        }
        fprintf(logfile, "\n");
    }

    fclose(logfile);
    free(data);
    return 0;
}
