// UPD Multicast on Arduino
// https://github.com/arduino/Arduino/pull/1531

// http://www.cs.ucsb.edu/~almeroth/classes/W01.176B/hw2/examples/udp-client.c
// http://www.ibm.com/developerworks/linux/tutorials/l-sock2/section5.html

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
#include <errno.h>

#define USE_CONNECTED_UDP


typedef struct {
   int socket_fd;
   int serial_fd;
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

   app_t* app = (app_t*) userdata;
   ssize_t res;

#ifndef USE_CONNECTED_UDP
   struct sockaddr_in sender_addr;
   socklen_t sender_addr_len = sizeof(sender_addr);
#endif

#ifdef USE_CONNECTED_UDP
   res = recv(app->socket_fd, data, len, 0);
#else
   res = recvfrom(app->socket_fd, data, len, 0, (struct sockaddr*) &sender_addr, &sender_addr_len);
#endif

   if (res < 0) {
      printf("transport_read: error %d - %s\n", errno, strerror(errno));      
   } else {
#ifdef USE_CONNECTED_UDP
      printf("transport_read: received %d octets\n", (int) res);
#else
      printf("transport_read: received %d octets from %s:%d\n", (int) res, inet_ntoa(sender_addr.sin_addr), ntohs(sender_addr.sin_port));
#endif      
   }

   return res;
}


// Transport writer function used by the SRDP channel
//
ssize_t transport_write (void* userdata, const uint8_t* data, size_t len) {

   app_t* app = (app_t*) userdata;
   ssize_t res;

#ifdef USE_CONNECTED_UDP
   /*
    * Send data over connected UDP socket.
    */
   res = send(app->socket_fd, data, len, 0);
#else
   /*
    * Send data over unconnected UDP socket.
    */
   res = sendto(app->socket_fd, data, len, 0, (struct sockaddr*) &(app->host_addr), sizeof(app->host_addr));
#endif

   if (res < 0) {
      printf("transport_write: error %d - %s\n", errno, strerror(errno));      
   } else {
      printf("transport_write: %d\n", (int) res);
   }

   return res;
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



int main(int argc, char**argv)
{
   if (argc != 2) {
      printf("Usage: udp_adapter <SRDP host IP>\n");
      return -1;
   }

   int stopped = 0;
   int res = 0;
   int fdmax = 0;
   fd_set readfds;
   //struct timeval timeout;

   app_t app;
   srdp_channel_t channel;

   app.serial_fd = 0;


   // Create a non-blocking UDP socket for SRDP-over-UDP.
   //
   //app.socket_fd = socket(AF_INET, SOCK_DGRAM, 0);
   app.socket_fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
   fcntl(app.socket_fd, O_NONBLOCK);


   // Configure socket for listening.
   // Note: You MUST first call bind(), and then connect()!
   //
   memset(&app.listen_addr, 0, sizeof(app.listen_addr));
   app.listen_addr.sin_family = AF_INET;
   app.listen_addr.sin_addr.s_addr = htonl(INADDR_ANY);
   app.listen_addr.sin_port = htons(SRDP_UDP_PORT);

   res = bind(app.socket_fd, (struct sockaddr*) &app.listen_addr, sizeof(app.listen_addr));
   if (res < 0) {
      printf("socket bind error: %d - %s\n", errno, strerror(errno));
   }

   // SRDP host IP/port. We will determine this by using mDNS/DNS-SD based
   // service discovery later.
   //
   memset(&app.host_addr, 0, sizeof(app.host_addr));
   app.host_addr.sin_family = AF_INET;
   app.host_addr.sin_addr.s_addr = inet_addr(argv[1]);
   app.host_addr.sin_port = htons(SRDP_UDP_PORT);

#ifdef USE_CONNECTED_UDP
   // SRDP clients talk to one and only one SRDP host, so we connect the UDP socket
   //
   res = connect(app.socket_fd, (struct sockaddr*) &app.host_addr, sizeof(app.host_addr));
   if (res < 0) {
      printf("socket connect error: %d - %s\n", errno, strerror(errno));
   }
#endif

   // highest FD in our FD sets .. needed for select()
   //
   fdmax = (app.socket_fd > app.serial_fd ? app.socket_fd : app.serial_fd) + 1;

   // initalize SRDP channel
   //
   srdp_init(&channel,
             transport_write, transport_read,
             register_write, register_read,
             log_message,
             &app);

   // enter our event dispatching loop ..
   //
   while (!stopped)
   {
      printf("Loop ...\n");

      // Note: both the FD set and the timeout MUST BE reinitialized on every select()!

      //timeout.tv_sec  = 0;
      //timeout.tv_usec = 0;

      FD_ZERO(&readfds);
      //FD_SET(app.serial_fd, &readfds);
      FD_SET(app.socket_fd, &readfds);

      //res = select(fdmax, &readfds, NULL, NULL, &timeout);
      res = select(fdmax, &readfds, NULL, NULL, NULL);

      if (res < 0) {
         printf("select(): error %d - %s\n", errno, strerror(errno));
         stopped = 1;
      }
      else if (res == 0) {
         printf("select(): timeout\n");
      }
      else {
         // process incoming SRDP protocol traffic
         //
         if (FD_ISSET(app.socket_fd, &readfds)) {
            srdp_loop(&channel);
         }

         // process other FDs here ..
      }
   }

   return 0;
}
