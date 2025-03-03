#include "mqtt/async_client.h"
#include "mqtt/client.h"
#include <string>

const std::string SERVER_ADDRESS{"tcp://localhost:1883"};
const std::string CLIENT_ID{"consume"};

int main() {
    mqtt::connect_options connOpts;
    connOpts.set_keep_alive_interval(20);
    connOpts.set_clean_session(true);

    mqtt::async_client cli_async(SERVER_ADDRESS, CLIENT_ID);
    mqtt::client cli(SERVER_ADDRESS, CLIENT_ID);

#ifdef TEST_SSL_OPTION
    // Build the connect options, including SSL and a LWT message.
    // auto sslopts = mqtt::ssl_options_builder(); // This was added in v1.2.0
    auto sslopts = mqtt::ssl_options();
#endif

    return 0;
}
