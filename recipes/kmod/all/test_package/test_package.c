#include "libkmod.h"
#include <stdio.h>
#include <stdlib.h>

int main() {
    struct kmod_ctx *ctx = kmod_new(NULL, NULL);
    if (ctx) {
        struct kmod_list *list, *mod;
        if (kmod_module_new_from_loaded(ctx, &list) >= 0) {
            kmod_list_foreach(mod, list) {
                struct kmod_module *kmod = kmod_module_get_module(mod);
                printf("%s\n", kmod_module_get_name(kmod));
            }
            kmod_module_unref_list(list);
        }
        kmod_unref(ctx);
    }
    return EXIT_SUCCESS;
}
