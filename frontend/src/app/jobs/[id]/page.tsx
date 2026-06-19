'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import Nav from '@/components/Nav';

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  useEffect(() => {
    if (!localStorage.getItem('token')) router.replace('/login');
  }, [router]);

  const { data: job, isLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.getValidationJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'SUCCEEDED' || status === 'FAILED' ? false : 2000;
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="flex items-center justify-center py-32">
          <div className="flex items-center gap-3 text-slate-400 animate-pulse">
            <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading job details...
          </div>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="flex flex-col items-center justify-center py-32 text-center">
          <div className="text-5xl mb-4">🔍</div>
          <p className="text-red-400 font-medium">Job not found</p>
          <Link href="/jobs" className="text-brand-400 text-sm mt-2 hover:underline">← Back to jobs</Link>
        </div>
      </div>
    );
  }

  const stats = job.stats as {
    total_rows?: number;
    valid_rows?: number;
    invalid_rows?: number;
    valid_percentage?: number;
    errors_by_code?: Record<string, number>;
  } | null;

  const statusConfig: Record<string, { badge: string; barClass: string; icon: string }> = {
    SUCCEEDED: { badge: 'status-succeeded', barClass: 'progress-bar-fill-success', icon: '✅' },
    FAILED: { badge: 'status-failed', barClass: 'progress-bar-fill-error', icon: '❌' },
    RUNNING: { badge: 'status-running', barClass: 'progress-bar-fill', icon: '⚡' },
    PENDING: { badge: 'status-pending', barClass: 'progress-bar-fill', icon: '⏳' },
  };

  const config = statusConfig[job.status] || statusConfig.PENDING;

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Breadcrumb */}
        <Link href="/jobs" className="inline-flex items-center gap-1 text-sm text-brand-400 hover:text-brand-300 mb-6 transition-colors animate-fade-in">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to jobs
        </Link>

        {/* Header */}
        <div className="mb-8 animate-fade-in-up">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
                <span>{config.icon}</span>
                Validation Job
              </h1>
              <p className="text-slate-500 font-mono text-sm">{job.id}</p>
            </div>
            <span className={`status-badge ${config.badge} text-sm`}>{job.status}</span>
          </div>
        </div>

        {/* Progress Card */}
        <div className="glass-card p-6 mb-6 animate-fade-in-up stagger-1" style={{ animationFillMode: 'both' }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-slate-300">Progress</span>
            <span className="text-sm font-mono text-brand-400 font-medium">{Math.round(job.progress)}%</span>
          </div>
          <div className="progress-bar h-3 rounded-full">
            <div className={`h-full rounded-full ${config.barClass}`} style={{ width: `${job.progress}%` }} />
          </div>
          <div className="grid grid-cols-2 gap-4 mt-5 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Dataset:</span>
              <span className="text-slate-200 capitalize font-medium">{job.dataset_type}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Rule set:</span>
              <span className="text-slate-200 font-medium">{job.rule_set}</span>
            </div>
          </div>
          {job.error_message && (
            <div className="mt-4 text-sm text-red-400 bg-red-500/10 border border-red-500/20 p-4 rounded-xl flex items-start gap-2">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {job.error_message}
            </div>
          )}
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatCard label="Total Rows" value={stats.total_rows ?? 0} icon="📊" color="text-brand-400" delay={2} />
            <StatCard label="Valid Rows" value={stats.valid_rows ?? 0} icon="✅" color="text-emerald-400" delay={3} />
            <StatCard label="Invalid Rows" value={stats.invalid_rows ?? 0} icon="⚠️" color="text-red-400" delay={4} />
            <StatCard label="Valid %" value={`${stats.valid_percentage ?? 0}%`} icon="📈" color="text-purple-400" delay={5} />
          </div>
        )}

        {/* Errors by Type */}
        {stats?.errors_by_code && Object.keys(stats.errors_by_code).length > 0 && (
          <div className="glass-card p-6 mb-6 animate-fade-in-up stagger-4" style={{ animationFillMode: 'both' }}>
            <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
              <span>🐛</span> Errors by Type
            </h2>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.errors_by_code).map(([code, count]) => (
                <span
                  key={code}
                  className="px-3 py-1.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-xs font-medium flex items-center gap-1.5"
                >
                  <span className="font-mono">{code}</span>
                  <span className="bg-red-500/20 px-1.5 py-0.5 rounded text-red-300">{count}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Download Results */}
        {job.output_files.length > 0 && (
          <div className="glass-card p-6 animate-fade-in-up stagger-5" style={{ animationFillMode: 'both' }}>
            <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
              <span>📥</span> Download Results
            </h2>
            <div className="space-y-2">
              {job.output_files.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.04] transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-brand-500/15 flex items-center justify-center">
                      <svg className="w-5 h-5 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{f.filename}</p>
                      <p className="text-xs text-slate-500">
                        {f.file_type}
                        {f.row_count != null && ` · ${f.row_count.toLocaleString()} rows`}
                        {' · '}{(f.file_size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  {f.download_url && (
                    <a
                      href={f.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-primary text-sm flex items-center gap-1.5"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function StatCard({ label, value, icon, color, delay }: {
  label: string;
  value: string | number;
  icon: string;
  color: string;
  delay: number;
}) {
  return (
    <div
      className="glass-card-hover p-5 animate-fade-in-up"
      style={{ animationDelay: `${delay * 100}ms`, animationFillMode: 'both' }}
    >
      <div className="text-lg mb-2">{icon}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
    </div>
  );
}
