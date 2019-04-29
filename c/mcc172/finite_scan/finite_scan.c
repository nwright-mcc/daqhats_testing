#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <daqhats/daqhats.h>

const char* default_filename = "./test.csv";


int read_args(int argc, char **argv, uint8_t* address, int* channel, 
    double* sample_rate_per_channel, uint32_t* samples, char* filename) 
{
	int c;

	opterr = 0;

	while ((c = getopt(argc, argv, "ha:c:f:n:o:")) != -1) {
		switch (c) {
			case 'a':
				*address = atoi(optarg);
				break;
			case 'c':
				*channel = atoi(optarg);
				break;
            case 'f':
                *sample_rate_per_channel = atof(optarg);
                break;
            case 'n':
                *samples = strtoul(optarg, NULL, 10);
                break;
			case 'h':
				return 1;
				break;
            case 'o':
                strcpy(filename, optarg);
                break;
			case '?':
				if ((optopt == 'c') || (optopt == 'a') || (optopt == 'f') ||
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
    uint16_t status;
    double* data;
    double sample_rate_per_channel;
    FILE* logfile;
    int index;
    int channel;
    int result;
    uint8_t clock_source;
    char filename[256];
    uint8_t synced;

    sample_rate_per_channel = 51200.0;
    samples_per_channel = 51200;
    address = 0;
    channel = 0;
    strcpy(filename, default_filename);
    
	if (read_args(argc, argv, &address, &channel, &sample_rate_per_channel,
        &samples_per_channel, filename) != 0) 
    {
		fprintf(stderr, 
			"Usage: %s [-a address] [-c channel] [-f frequency] [-n samples] [-o file]\n"
			"    -a address: address [0-7] of the HAT to scan (default is 0)\n"
			"    -c channel: channel number to scan (default is 0)\n"
            "    -f frequency: ADC sampling frequency (default is 51200)\n"
            "    -n samples: number of samples (default is 51200)\n"
            "    -o file: output file name (default is ./test.csv)\n",
            argv[0]);
		return 1;
	}

    channels = 1 << channel;
    num_channels = 1;
    options = 0;

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

#if 1
    // configure ADC clock
    clock_source = 0;   // local mode
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
        result = mcc172_a_in_clock_config_read(address, &clock_source, &sample_rate_per_channel, &synced);
        if (result != RESULT_SUCCESS)
        {
            printf("clock_config_read returned %d\n", result);
            mcc172_close(address);
            return 1;
        }
    } while (synced == 0);
    printf("ADC clock set to %.1f Hz\n", sample_rate_per_channel);
#endif
    
    printf("Scanning %d samples from channel %d...\n", samples_per_channel, channel);
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
        for (channel = 0; channel < num_channels; channel++)
        {
            fprintf(logfile, "%f,", data[(index * num_channels) + channel]);
        }
        fprintf(logfile, "\n");
    }
    
    fclose(logfile);
    free(data);
    return 0;
}
