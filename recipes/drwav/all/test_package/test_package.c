#include "dr_wav.h"
#include <stdio.h>

int main(void) {
    const char *version = drwav_version_string();
    printf("dr_wav version: %s\n", version);

    return 0;
}
