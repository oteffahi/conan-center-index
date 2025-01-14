#include <apriltag.h>
#include <common/image_u8.h>
#include <tagStandard41h12.h>

#include <stdio.h>

int main() {
    apriltag_detector_t *td = apriltag_detector_create();
    apriltag_family_t *tf = tagStandard41h12_create();
    apriltag_detector_add_family(td, tf);

    tagStandard41h12_destroy(tf);
    apriltag_detector_destroy(td);

    printf("Apriltag test_package ran successfully\n");

    return 0;
}
