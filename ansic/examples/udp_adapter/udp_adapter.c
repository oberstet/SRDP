// UPD Multicast on Arduino
// https://github.com/arduino/Arduino/pull/1531

// http://www.cs.ucsb.edu/~almeroth/classes/W01.176B/hw2/examples/udp-client.c
// http://www.ibm.com/developerworks/linux/tutorials/l-sock2/section5.html

#define SRDP_DEBUG_TRANSPORT_ECHO
#include <srdp.h>

#include <unistd.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <fcntl.h>


typedef struct {
   int socket_fd;
   struct sockaddr_in host_addr;
   struct sockaddr_in listen_addr;
} app_t;

// Custom logger for SRDP. We turn on a red LED to signal errors.
//
void log_message (const char* msg, int level) {
   //printf(msg);
}


// Transport reader function used by the SRDP channel
//
ssize_t transport_read (void* userdata, uint8_t* data, size_t len) {

   ssize_t res;
   app_t* app = (app_t*) userdata;
   res = recvfrom(app->socket_fd, data, len, 0, NULL, NULL);
   printf("transport_read: %d\n", (int) res);
   return res;
}


// Transport writer function used by the SRDP channel
//
ssize_t transport_write (void* userdata, const uint8_t* data, size_t len) {

   int res;
   app_t* app = (app_t*) userdata;

   res = sendto(app->socket_fd,
          data,
          len,
          0,
          (struct sockaddr*) &(app->host_addr),
          sizeof(app->host_addr));

   printf("transport_write: %d\n", res);
   return len;
}


// Register read handler called when host requests to read a register
//
int register_read (void* userdata, int dev, int reg, int pos, int len, uint8_t* data) {
   return SRDP_ERR_NOT_IMPLEMENTED;
}


// Register write handler called when host requests to write a register
//
int register_write(void* userdata, int dev, int reg, int pos, int len, const uint8_t* data) {
   return SRDP_ERR_NOT_IMPLEMENTED;
}


#define MAX 65536
uint8_t buffer[MAX];


int main(int argc, char**argv)
{
   int stopped;
   int res;
   int serial_fd;
   int max_fd;
   fd_set input;
   //struct timeval timeout;

   app_t app;

   srdp_channel_t channel;

   stopped = 0;

   app.socket_fd = socket(AF_INET, SOCK_DGRAM, 0);
   //fcntl(app.socket_fd, O_NONBLOCK);
   serial_fd = 0;

   memset(&app.host_addr, 0, sizeof(app.host_addr));
   app.host_addr.sin_family = AF_INET;
   app.host_addr.sin_addr.s_addr = inet_addr("192.168.56.101");
   app.host_addr.sin_port = htons(9000);

   memset(&app.listen_addr, 0, sizeof(app.listen_addr));
   app.listen_addr.sin_family = AF_INET;
   app.listen_addr.sin_addr.s_addr = htonl(INADDR_ANY);
   //app.listen_addr.sin_addr.s_addr = inet_addr("192.168.56.102");
   //app.listen_addr.sin_port = htons(0);
   app.listen_addr.sin_port = htons(9000);

   res = bind(app.socket_fd,
              (struct sockaddr*) &(app.listen_addr),
              sizeof(app.listen_addr));

   if (res < 0) {
      printf("bind error\n");
   }

   max_fd = (app.socket_fd > serial_fd ? app.socket_fd : serial_fd) + 1;

   //timeout.tv_sec  = 0;
   //timeout.tv_usec = 0;

   // initalize SRDP channel
   //
   srdp_init(&channel,
             transport_write, transport_read,
             register_write, register_read,
             log_message,
             &app);


   while (!stopped)
   {
      printf("Loop ...\n");

      FD_ZERO(&input);
      //FD_SET(serial_fd, &input);
      FD_SET(app.socket_fd, &input);

      //res = select(max_fd, &input, NULL, NULL, &timeout);
      res = select(max_fd, &input, NULL, NULL, NULL);
      //printf("select()\n");

      if (res < 0) {
         // socket error
         printf("error");
         stopped = 1;
      }
      else if (res == 0) {
         // timeout
         printf("timeout");
         stopped = 1;
      }
      else {
         if (FD_ISSET(app.socket_fd, &input)) {
            srdp_loop(&channel);
         }
      }
   }

   return 0;
}
