'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, uploadFileChunked } from '@/lib/api';
import Nav from '@/components/Nav';

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [datasetType, setDatasetType] = useState('orders');
  const [ruleSet, setRuleSet] = useState('default');
  const [validOnly, setValidOnly] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!localStorage.getItem('token')) router.replace('/login');
  }, [router]);

  const { data: ruleSets } = useQuery({ queryKey: ['rules'], queryFn: api.listRuleSets });

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && (droppedFile.name.endsWith('.csv') || droppedFile.name.endsWith('.tsv') || droppedFile.name.endsWith('.txt'))) {
      setFile(droppedFile);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  function formatFileSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError('');
    setBusy(true);
    setProgress(0);
    setMessage('Starting upload...');

    try {
      const session = await uploadFileChunked(file, (pct, msg) => {
        setProgress(pct);
        setMessage(msg);
      });

      setMessage('Creating validation job...');
      setProgress(95);
      const job = await api.createValidationJob(session.id, datasetType, ruleSet, { valid_only: validOnly });
      setProgress(100);
      setMessage('Job created! Redirecting...');
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="max-w-2xl mx-auto px-6 py-8">
        <div className="mb-8 animate-fade-in-up">
          <h1 className="text-3xl font-bold text-white mb-1">
            Upload <span className="gradient-text">&amp; Validate</span>
          </h1>
          <p className="text-slate-400">Upload your CSV files for validation and cleaning.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6 animate-fade-in-up stagger-2" style={{ animationFillMode: 'both' }}>
          {/* Drag & Drop Zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`relative glass-card p-8 text-center cursor-pointer transition-all duration-300 group ${
              isDragOver
                ? 'border-brand-500/50 bg-brand-500/[0.08] scale-[1.01]'
                : file
                  ? 'border-emerald-500/30 bg-emerald-500/[0.04]'
                  : 'hover:border-white/[0.15] hover:bg-white/[0.06]'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.tsv,.txt"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="hidden"
            />
            
            {file ? (
              <div className="animate-scale-in">
                <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-7 h-7 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="text-white font-medium">{file.name}</p>
                <p className="text-slate-400 text-sm mt-1">{formatFileSize(file.size)}</p>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="mt-3 text-xs text-slate-500 hover:text-red-400 transition-colors"
                >
                  Remove file
                </button>
              </div>
            ) : (
              <>
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 transition-all duration-300 ${
                  isDragOver ? 'bg-brand-500/20 scale-110' : 'bg-white/[0.06] group-hover:bg-white/[0.08]'
                }`}>
                  <svg className={`w-7 h-7 transition-colors ${isDragOver ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <p className="text-slate-300 font-medium">
                  {isDragOver ? 'Drop your file here' : 'Drag & drop your CSV file here'}
                </p>
                <p className="text-slate-500 text-sm mt-1">or click to browse</p>
                <p className="text-slate-600 text-xs mt-3">Supports CSV, TSV, TXT • Chunked resumable uploads for large files</p>
              </>
            )}
          </div>

          {/* Settings */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="glass-card p-5">
              <label className="block text-sm font-medium text-slate-300 mb-2">Dataset Type</label>
              <select
                value={datasetType}
                onChange={(e) => setDatasetType(e.target.value)}
                className="select-field"
              >
                <option value="orders">📦 Orders</option>
                <option value="products">🏷️ Products</option>
                <option value="payments">💳 Payments</option>
              </select>
            </div>

            <div className="glass-card p-5">
              <label className="block text-sm font-medium text-slate-300 mb-2">Rule Set</label>
              <select
                value={ruleSet}
                onChange={(e) => setRuleSet(e.target.value)}
                className="select-field"
              >
                {(ruleSets || [{ id: 'default', name: 'Default Transaction Rules' }]).map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Options */}
          <div className="glass-card p-5">
            <label className="flex items-center gap-3 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={validOnly}
                  onChange={(e) => setValidOnly(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-10 h-6 bg-white/[0.08] rounded-full peer-checked:bg-brand-600 transition-colors duration-200" />
                <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-transform duration-200 peer-checked:translate-x-4" />
              </div>
              <div>
                <span className="text-sm font-medium text-slate-300">Output only valid rows</span>
                <p className="text-xs text-slate-500">Exclude rows with validation errors from the output</p>
              </div>
            </label>
          </div>

          {/* Progress */}
          {busy && (
            <div className="glass-card p-5 animate-scale-in">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-slate-300 flex items-center gap-2">
                  <svg className="animate-spin w-4 h-4 text-brand-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {message}
                </span>
                <span className="text-brand-400 font-mono font-medium">{progress}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 text-sm text-red-400 bg-red-500/10 border border-red-500/20 px-4 py-3 rounded-xl animate-scale-in">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <div>
                <p className="font-medium">Upload Failed</p>
                <p className="text-red-400/80 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={busy || !file}
            className="btn-primary w-full py-3.5 text-base flex items-center justify-center gap-2"
          >
            {busy ? (
              <>
                <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Processing...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                Upload &amp; Start Validation
              </>
            )}
          </button>
        </form>
      </main>
    </div>
  );
}
