#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <daqhats/daqhats.h>

const char* filename = "test.csv";

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
    double sample_rate_per_channel = 51200;
    FILE* logfile;
    int index;
    int channel;
    int result;
    double value;
    uint8_t clock_source;

    // Use MCC 172 at address 3
    address = 3;
    num_channels = 2;
    channels = 0x03;
    samples_per_channel = 51200;
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
    
    //mcc172_close(address);
    //return 0;
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
            printf("Read: %d %X %d %d\n", result, status, samples_read_per_channel, samples_read);
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
