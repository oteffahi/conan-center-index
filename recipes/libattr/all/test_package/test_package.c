#include <attr/attributes.h>
#include <sys/types.h>

int main() {
    char value[255];
    int len = sizeof(value);
    const char *path = "file_not_exist.txt";
    const char *attr = "attr_not_exist";
    attr_get(path, attr, value, &len, 0);
    return 0;
}
