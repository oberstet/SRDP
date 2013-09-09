// UPD Multicast on Arduino
// https://github.com/arduino/Arduino/pull/1531

#include <srdp.h>

int main () {

   srdp_channel_t channel;
   srdp_init(&channel, 0, 0, 0, 0, 0, 0);

   printf("Done.\n");
   return 0;
}
