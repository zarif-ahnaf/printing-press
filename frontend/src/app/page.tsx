'use client';

import { useState, useCallback, type ReactNode } from 'react';
import { useDropzone } from 'react-dropzone';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle, FileText, Upload, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface PdfResult {
    file: File;
    totalPages: number;
    nonBlankPages: number;
    error?: string;
}

export default function Page() {
    const [files, setFiles] = useState<File[]>([]);
    const [results, setResults] = useState<PdfResult[]>([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        const pdfFiles = acceptedFiles.filter(
            (file) =>
                file.type === 'application/pdf' || file.name.endsWith('.pdf')
        );

        if (pdfFiles.length !== acceptedFiles.length) {
            setError('Only PDF files are allowed');
            setTimeout(() => setError(null), 3000);
        }

        setFiles((prev) => [...prev, ...pdfFiles]);
        setResults((prev) => [
            ...prev,
            ...pdfFiles.map((file) => ({
                file,
                totalPages: 0,
                nonBlankPages: 0,
            })),
        ]);
    }, []);

    const removeFile = (fileName: string) => {
        setFiles(files.filter((f) => f.name !== fileName));
        setResults(results.filter((r) => r.file.name !== fileName));
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf'],
        },
        multiple: true,
    });

    const processFiles = async () => {
        if (files.length === 0) return;

        setIsProcessing(true);
        setError(null);

        const newResults = [...results];

        try {
            for (const [index, file] of files.entries()) {
                if (newResults[index].totalPages > 0 || newResults[index].error)
                    continue;

                const reader = new FileReader();
                const base64 = await new Promise<string>((resolve, reject) => {
                    reader.onload = () => resolve(reader.result as string);
                    reader.onerror = reject;
                    reader.readAsDataURL(file);
                });

                const response = await fetch('/api/count', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ file: base64 }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    newResults[index] = {
                        ...newResults[index],
                        error: errorData.error || 'Processing failed',
                    };
                } else {
                    const data = await response.json();
                    newResults[index] = {
                        ...newResults[index],
                        totalPages: data.totalPages,
                        nonBlankPages: data.nonBlankPages,
                    };
                }

                setResults([...newResults]);
            }
        } catch (err) {
            setError('Unexpected error during processing');
            console.error(err);
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <div className="container mx-auto py-8 md:py-12 px-4">
            <Card className="max-w-2xl mx-auto">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl font-bold">
                        PDF Page Counter
                    </CardTitle>
                    <CardDescription>
                        Upload PDFs to count non-blank pages. Blank pages are
                        detected by pixel analysis.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div
                        {...getRootProps()}
                        className={cn(
                            'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
                            isDragActive
                                ? 'border-primary bg-primary/5'
                                : 'border-muted-foreground/25 hover:border-primary/50'
                        )}
                    >
                        <input {...getInputProps()} />
                        <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                        <p className="text-lg font-medium">
                            {isDragActive
                                ? 'Drop your PDFs here'
                                : 'Drag & drop PDF files here'}
                        </p>
                        <p className="text-sm text-muted-foreground mt-2">
                            or click to browse files (supports multiple)
                        </p>
                    </div>

                    {error && (
                        <Alert variant="destructive" className="mt-4">
                            <AlertCircle className="h-4 w-4" />
                            <AlertTitle>Error</AlertTitle>
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    {files.length > 0 && (
                        <div className="mt-6 space-y-4">
                            <div className="flex justify-between items-center">
                                <h3 className="font-medium">
                                    Selected Files ({files.length})
                                </h3>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                        setFiles([]);
                                        setResults([]);
                                    }}
                                >
                                    Clear All
                                </Button>
                            </div>

                            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                                {files.map((file, index) => {
                                    const result = results.find(
                                        (r) => r.file.name === file.name
                                    );
                                    const isProcessingFile =
                                        isProcessing &&
                                        !result?.totalPages &&
                                        !result?.error;

                                    return (
                                        <div
                                            key={file.name}
                                            className={cn(
                                                'flex items-center justify-between p-3 border rounded-lg',
                                                'bg-card hover:bg-accent/30 transition-colors'
                                            )}
                                        >
                                            <div className="flex items-center space-x-3 min-w-0">
                                                <FileText className="h-5 w-5 text-primary flex-shrink-0" />
                                                <div className="truncate max-w-[180px]">
                                                    <p className="font-medium truncate">
                                                        {file.name}
                                                    </p>
                                                    <p className="text-xs text-muted-foreground">
                                                        {(
                                                            file.size /
                                                            1024 /
                                                            1024
                                                        ).toFixed(2)}{' '}
                                                        MB
                                                    </p>
                                                </div>
                                            </div>

                                            <div className="flex items-center space-x-2">
                                                {isProcessingFile ? (
                                                    <Progress
                                                        value={33}
                                                        className="w-20 h-2"
                                                    />
                                                ) : result?.error ? (
                                                    <Badge variant="destructive">
                                                        Error
                                                    </Badge>
                                                ) : result?.totalPages ? (
                                                    <Badge variant="secondary">
                                                        {result.nonBlankPages}/
                                                        {result.totalPages}
                                                    </Badge>
                                                ) : null}

                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8"
                                                    onClick={() =>
                                                        removeFile(file.name)
                                                    }
                                                >
                                                    <X className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            <Button
                                className="w-full mt-2"
                                onClick={processFiles}
                                disabled={isProcessing || files.length === 0}
                            >
                                {isProcessing
                                    ? 'Processing...'
                                    : 'Count Non-Blank Pages'}
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
