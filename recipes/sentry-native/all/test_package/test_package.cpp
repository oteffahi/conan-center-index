#include "sentry.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {
    sentry_options_t *options = sentry_options_new();

    sentry_options_set_environment(options, "Production");
    sentry_options_set_release(options, "test-example-release");

    sentry_init(options);

    sentry_shutdown();
}
