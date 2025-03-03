#include <libfreenect/libfreenect.h>
#include <stdio.h>
#include <string.h>

int main() {
    freenect_context *fn_ctx = NULL;
    int ret = freenect_init(&fn_ctx, NULL);
    if (ret < 0)
        return ret;

    freenect_shutdown(fn_ctx);
    return 0;
}
