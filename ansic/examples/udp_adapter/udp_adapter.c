// UPD Multicast on Arduino
// https://github.com/arduino/Arduino/pull/1531

// http://www.cs.ucsb.edu/~almeroth/classes/W01.176B/hw2/examples/udp-client.c
// http://www.ibm.com/developerworks/linux/tutorials/l-sock2/section5.html

#include <srdp.h>


// Custom logger for SRDP. We turn on a red LED to signal errors.
//
void log_message (const char* msg, int level) {
   printf(msg);
}


// Transport reader function used by the SRDP channel
//
ssize_t transport_read (void* userdata, uint8_t* data, size_t len) {
   return 0;
}


// Transport writer function used by the SRDP channel
//
ssize_t transport_write (void* userdata, const uint8_t* data, size_t len) {
   return 0;
}


// Register read handler called when host requests to read a register
//
int register_read (void* userdata, int dev, int reg, int pos, int len, uint8_t* data) {
   return 0;
}


// Register write handler called when host requests to write a register
//
int register_write(void* userdata, int dev, int reg, int pos, int len, const uint8_t* data) {
   return 0;
}


int main () {

   srdp_channel_t channel;

   // initalize SRDP channel
   //
   srdp_init(&channel,
             transport_write, transport_read,
             register_write, register_read,
             log_message,
             0);

   printf("Done.\n");
   return 0;
}
