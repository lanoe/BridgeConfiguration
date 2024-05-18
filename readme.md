# Bridge Configuration Tool

## Prerequisites

- Bridge board connected to your LAN
- SDCard with Linux operating system

## How to build

- Run `git clone ssh://git@gitlab.dsinstruments.fr:2222/BridgeConfiguration.git
- Run `cd BridgeConfiguration`
- Run `build.sh`
    - Installs Python dependencies
    - Launch BridgeConfig.service

## Usage

- Go to `http://<bridge_board_ip>:4242` (the page should open automatically in your default browser) 
- Select the Dandelion server which will be the bridge's target server
- Enter Dandelion credentials, then click the Login button 
- Enter the bridge GUID which corresponds to the uSOM eMMC
- Click on the Configure button, and wait for the process to end
- And Voila!

## Test

- Run `run_test_server.sh`
- This will launch the same environment as production, but it will use development configuration instead.
- Go to `http://<bridge_board_ip>:5000` (the page should open automatically in your default browser)
- Enter Dandelion dev credentials, then click the Login button 
- Select the Dandelion server which will be the bridge's target server
- Enter the value `100` as Bridge GUID
- Click on the Configure button, and wait for the process to end
- Run `validate_tests.sh`
- The result should be `SUCCESS | All the files are valid.`
