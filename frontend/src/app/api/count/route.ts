import { NextRequest } from 'next/server';
import { getDocument } from 'pdfjs-dist/legacy/build/pdf';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as crypto from 'crypto';

const PIXEL_DARKNESS_THRESHOLD = 10;
const MIN_NON_BLANK_PIXEL_RATIO = 0.0005;

interface Canvas {
    getContext(type: '2d'): CanvasRenderingContext2D;
    width: number;
    height: number;
}

function createNodeCanvas(width: number, height: number): Canvas {
    const { createCanvas } = require('canvas');
    return createCanvas(Math.ceil(width), Math.ceil(height));
}

function isPageBlank(
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number
): boolean {
    const imageData = ctx.getImageData(0, 0, width, height);
    const data = imageData.data;
    let nonBlankPixelCount = 0;
    const sampleStep = 5;

    for (let y = 0; y < height; y += sampleStep) {
        for (let x = 0; x < width; x += sampleStep) {
            const idx = (y * width + x) * 4;
            const r = data[idx];
            const g = data[idx + 1];
            const b = data[idx + 2];
            if (
                r < 255 - PIXEL_DARKNESS_THRESHOLD ||
                g < 255 - PIXEL_DARKNESS_THRESHOLD ||
                b < 255 - PIXEL_DARKNESS_THRESHOLD
            ) {
                nonBlankPixelCount++;
            }
        }
    }

    const totalSampled =
        Math.ceil(height / sampleStep) * Math.ceil(width / sampleStep);
    return nonBlankPixelCount / totalSampled < MIN_NON_BLANK_PIXEL_RATIO;
}

function extractBase64(dataUrl: string): string | null {
    if (dataUrl.startsWith('')) {
        return dataUrl.split(',')[1] || null;
    }
    if (dataUrl.includes('base64,')) {
        return dataUrl.split('base64,')[1] || null;
    }
    if (/^[A-Za-z0-9+/]*={0,2}$/.test(dataUrl)) {
        return dataUrl;
    }
    return null;
}

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const fileData: string = body.file;

        if (!fileData || typeof fileData !== 'string') {
            return Response.json(
                { error: 'File data is required' },
                { status: 400 }
            );
        }

        const base64 = extractBase64(fileData);
        if (!base64) {
            return Response.json(
                { error: 'Invalid base64-encoded PDF' },
                { status: 400 }
            );
        }

        if (!/^[A-Za-z0-9+/]*={0,2}$/.test(base64)) {
            return Response.json(
                { error: 'Malformed base64 data' },
                { status: 400 }
            );
        }

        const tempFilename = `pdf_${crypto
            .randomBytes(16)
            .toString('hex')}.pdf`;
        const tempFilePath = path.join(os.tmpdir(), tempFilename);

        fs.writeFileSync(tempFilePath, Buffer.from(base64, 'base64'));

        // ✅ Load PDF without worker
        const pdfDoc = await getDocument({
            url: tempFilePath,
        }).promise;

        const totalPages = pdfDoc.numPages;
        let nonBlankCount = 0;

        for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
            const page = await pdfDoc.getPage(pageNum);
            const viewport = page.getViewport({ scale: 0.5 });

            const canvas = createNodeCanvas(viewport.width, viewport.height);
            const ctx = canvas.getContext('2d');

            await page.render({
                canvasContext: ctx,
                canvas: canvas as any,
                viewport,
            }).promise;

            if (!isPageBlank(ctx, viewport.width, viewport.height)) {
                nonBlankCount++;
            }
        }

        await pdfDoc.destroy();
        fs.unlinkSync(tempFilePath);

        return Response.json({
            totalPages,
            nonBlankPages: nonBlankCount,
        });
    } catch (err: any) {
        console.error('PDF processing error:', err);
        return Response.json(
            { error: 'Failed to process PDF', message: err.message },
            { status: 500 }
        );
    }
}
