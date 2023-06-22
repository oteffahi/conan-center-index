#include <selinux/selinux.h>
#include <stdio.h>

int main() {
    if (is_selinux_enabled())
        printf("SELinux is enabled\n");
    else
        printf("SELinux is not enabled\n");
    return 0;
}
