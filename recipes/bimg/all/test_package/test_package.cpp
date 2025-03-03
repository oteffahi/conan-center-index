#include <bimg/bimg.h>
#include <bimg/decode.h>
#include <bx/allocator.h>
#include <bx/bx.h>

// An embedded 2x2 PNG image in RGB8 format with a red pixel, a green pixel, a blue pixel and a
// white pixel
const unsigned char img[129] = {
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44,
    0x52, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x02, 0x08, 0x02, 0x00, 0x00, 0x00, 0xfd,
    0xd4, 0x9a, 0x73, 0x00, 0x00, 0x00, 0x01, 0x73, 0x52, 0x47, 0x42, 0x00, 0xae, 0xce, 0x1c,
    0xe9, 0x00, 0x00, 0x00, 0x04, 0x67, 0x41, 0x4d, 0x41, 0x00, 0x00, 0xb1, 0x8f, 0x0b, 0xfc,
    0x61, 0x05, 0x00, 0x00, 0x00, 0x09, 0x70, 0x48, 0x59, 0x73, 0x00, 0x00, 0x0e, 0xc3, 0x00,
    0x00, 0x0e, 0xc3, 0x01, 0xc7, 0x6f, 0xa8, 0x64, 0x00, 0x00, 0x00, 0x16, 0x49, 0x44, 0x41,
    0x54, 0x18, 0x57, 0x63, 0x78, 0x2b, 0xa3, 0xa2, 0xb4, 0xd1, 0x87, 0xc1, 0xde, 0xe3, 0xcc,
    0xff, 0xff, 0xff, 0x01, 0x24, 0xec, 0x06, 0x9d, 0x64, 0xf4, 0x18, 0xdc, 0x00, 0x00, 0x00,
    0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82};

int main() {
    bx::DefaultAllocator defAlloc;
    bimg::ImageContainer *imageContainer = nullptr;
    imageContainer = bimg::imageParse(&defAlloc, (const void *)img, 129 * sizeof(char));
    BX_ASSERT(imageContainer->m_format == bimg::TextureFormat::RGB8, "Image incorrectly decoded.")
    bimg::imageFree(imageContainer);
    return 0;
}
