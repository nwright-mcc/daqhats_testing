# Tools for testing the MCC 172

To use this code:
1. Install the daqhats library per instructions.
2. Clone this repo with:
   
   ```sh
   cd ~
   git clone https://github.com/nwright-mcc/daqhats_testing.git
   ```

To acquire sample data to CSV:
1. Build the finite_scan code:
   ```sh
   cd ~/daqhats_testing/c/mcc172/finite_scan
   make
   ```
2. Run `./finite_scan -h` to get the list of options for using the program.

