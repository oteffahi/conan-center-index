#include "cbor.h"
#include <stdio.h>
#include <stdlib.h>

int main() {
    CborParser parser;
    CborValue it;
    size_t length;
    uint8_t *buf = (uint8_t *)malloc(sizeof(int[10]));
    CborError err = cbor_parser_init(buf, length, 0, &parser, &it);

    printf("Tinycbor test_package ran successfully \n");
    return 0;
}
