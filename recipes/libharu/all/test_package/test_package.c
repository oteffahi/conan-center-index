#include "hpdf.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void error_handler(HPDF_STATUS error_no, HPDF_STATUS detail_no, void *user_data) {
    printf("ERROR: error_no=%04X, detail_no=%u\n", (HPDF_UINT)error_no, (HPDF_UINT)detail_no);
    abort();
}

void print_grid(HPDF_Doc pdf, HPDF_Page page) {
    HPDF_REAL height = HPDF_Page_GetHeight(page);
    HPDF_REAL width = HPDF_Page_GetWidth(page);
    HPDF_Font font = HPDF_GetFont(pdf, "Helvetica", NULL);
    HPDF_UINT x, y;

    HPDF_Page_SetFontAndSize(page, font, 5);
    HPDF_Page_SetGrayFill(page, 0.5);
    HPDF_Page_SetGrayStroke(page, 0.8);

    /* Draw horizontal lines */
    y = 0;
    while (y < height) {
        if (y % 10 == 0)
            HPDF_Page_SetLineWidth(page, 0.5);
        else {
            if (HPDF_Page_GetLineWidth(page) != 0.25)
                HPDF_Page_SetLineWidth(page, 0.25);
        }

        HPDF_Page_MoveTo(page, 0, y);
        HPDF_Page_LineTo(page, width, y);
        HPDF_Page_Stroke(page);

        if (y % 10 == 0 && y > 0) {
            HPDF_Page_SetGrayStroke(page, 0.5);

            HPDF_Page_MoveTo(page, 0, y);
            HPDF_Page_LineTo(page, 5, y);
            HPDF_Page_Stroke(page);

            HPDF_Page_SetGrayStroke(page, 0.8);
        }

        y += 5;
    }

    /* Draw vertical lines */
    x = 0;
    while (x < width) {
        if (x % 10 == 0)
            HPDF_Page_SetLineWidth(page, 0.5);
        else {
            if (HPDF_Page_GetLineWidth(page) != 0.25)
                HPDF_Page_SetLineWidth(page, 0.25);
        }

        HPDF_Page_MoveTo(page, x, 0);
        HPDF_Page_LineTo(page, x, height);
        HPDF_Page_Stroke(page);

        if (x % 50 == 0 && x > 0) {
            HPDF_Page_SetGrayStroke(page, 0.5);

            HPDF_Page_MoveTo(page, x, 0);
            HPDF_Page_LineTo(page, x, 5);
            HPDF_Page_Stroke(page);

            HPDF_Page_MoveTo(page, x, height);
            HPDF_Page_LineTo(page, x, height - 5);
            HPDF_Page_Stroke(page);

            HPDF_Page_SetGrayStroke(page, 0.8);
        }

        x += 5;
    }

    /* Draw horizontal text */
    y = 0;
    while (y < height) {
        if (y % 10 == 0 && y > 0) {
            char buf[12];

            HPDF_Page_BeginText(page);
            HPDF_Page_MoveTextPos(page, 5, y - 2);
            snprintf(buf, 12, "%u", y);
            HPDF_Page_ShowText(page, buf);
            HPDF_Page_EndText(page);
        }

        y += 5;
    }

    /* Draw vertical text */
    x = 0;
    while (x < width) {
        if (x % 50 == 0 && x > 0) {
            char buf[12];

            HPDF_Page_BeginText(page);
            HPDF_Page_MoveTextPos(page, x, 5);
            snprintf(buf, 12, "%u", x);
            HPDF_Page_ShowText(page, buf);
            HPDF_Page_EndText(page);

            HPDF_Page_BeginText(page);
            HPDF_Page_MoveTextPos(page, x, height - 10);
            HPDF_Page_ShowText(page, buf);
            HPDF_Page_EndText(page);
        }

        x += 5;
    }

    HPDF_Page_SetGrayFill(page, 0);
    HPDF_Page_SetGrayStroke(page, 0);
}

int main() {
    HPDF_Doc pdf;
    HPDF_Page page;

    pdf = HPDF_New(error_handler, NULL);
    if (!pdf) {
        fprintf(stderr, "error: cannot create PdfDoc object\n");
        return 1;
    }
    page = HPDF_AddPage(pdf);
    print_grid(pdf, page);
    HPDF_SaveToFile(pdf, "test.pdf");

    HPDF_Free(pdf);
    return 0;
}
