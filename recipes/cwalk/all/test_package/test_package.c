#include <cwalk.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    char result[FILENAME_MAX];

    cwk_path_normalize("/var/log/weird/////path/.././..///", result, sizeof(result));

    return EXIT_SUCCESS;
}
