# Tools for testing the MCC 172

## To use this code:
1. Install the daqhats library per instructions.
2. Clone this repo with:
   
   ```sh
   cd ~
   git clone https://github.com/nwright-mcc/daqhats_testing.git
   ```

## To acquire sample data to CSV:
1. Build the finite_scan code:
   ```sh
   cd ~/daqhats_testing/c/mcc172/finite_scan
   make
   ```
2. Run `./finite_scan -h` to get the list of options for using the program.

## To acquire sample data directly in LabView:
1. Copy the VIs from ~/daqhats_testing/python/mcc172/labview to your LabView PC.
2. Run the server application on the Raspberry Pi:
   ```sh
   cd ~/daqhats_testing/python/mcc172
   sudo ./tcp_server.py
   ```
2. Open the VI "MCC 172 Noise.vi".  Enter the server IP address displayed by the 
   server in the correct field, then run the VI.  It will continuously read input
   data and display the measured FFT and noise information.  This can be used as
   an example to create additional VIs.
