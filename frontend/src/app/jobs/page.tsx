'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import Nav from '@/components/Nav';

function statusStyle(status: string) {
  switch (status) {
    case 'SUCCEEDED': return 'status-succeeded';
    case 'FAILED': return 'status-failed';
    case 'RUNNING': return 'status-running';
    default: return 'status-pending';
  }
}

export default function JobsListPage() {
  const router = useRouter();

  useEffect(() => {
    if (!localStorage.getItem('token')) router.replace('/login');
  }, [router]);

  const { data: jobs, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: api.listValidationJobs,
    refetchInterval: 5000,
  });

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8 animate-fade-in-up">
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">
              Validation <span className="gradient-text">Jobs</span>
            </h1>
            <p className="text-slate-400 text-sm">Track and manage your data validation tasks.</p>
          </div>
          <Link href="/upload" className="btn-primary flex items-center gap-2 text-sm">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Upload
          </Link>
        </div>

        <div className="glass-card overflow-hidden animate-fade-in-up stagger-2" style={{ animationFillMode: 'both' }}>
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-4 px-5 py-3 bg-white/[0.02] border-b border-white/[0.06] text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <div className="col-span-3">Job ID</div>
            <div className="col-span-2">Dataset</div>
            <div className="col-span-2">Status</div>
            <div className="col-span-2">Progress</div>
            <div className="col-span-3">Created</div>
          </div>

          {/* Loading */}
          {isLoading && (
            <div className="px-5 py-12 text-center">
              <div className="inline-flex items-center gap-2 text-slate-400">
                <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Loading jobs...
              </div>
            </div>
          )}

          {/* Rows */}
          {jobs?.map((job, i) => (
            <Link
              key={job.id}
              href={`/jobs/${job.id}`}
              className="grid grid-cols-12 gap-4 px-5 py-4 border-b border-white/[0.04] hover:bg-white/[0.03] transition-all duration-200 group items-center animate-fade-in-up"
              style={{ animationDelay: `${i * 50}ms`, animationFillMode: 'both' }}
            >
              <div className="col-span-3">
                <span className="font-mono text-xs text-brand-400 group-hover:text-brand-300 transition-colors">
                  {job.id.slice(0, 8)}...
                </span>
              </div>
              <div className="col-span-2 text-sm text-slate-300 capitalize">{job.dataset_type}</div>
              <div className="col-span-2">
                <span className={`status-badge ${statusStyle(job.status)}`}>{job.status}</span>
              </div>
              <div className="col-span-2">
                <div className="flex items-center gap-2">
                  <div className="flex-1 progress-bar">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        job.status === 'SUCCEEDED' ? 'progress-bar-fill-success' :
                        job.status === 'FAILED' ? 'progress-bar-fill-error' : 'progress-bar-fill'
                      }`}
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-500 font-mono w-8 text-right">{Math.round(job.progress)}%</span>
                </div>
              </div>
              <div className="col-span-3 flex items-center justify-between">
                <span className="text-sm text-slate-500">{new Date(job.created_at).toLocaleString()}</span>
                <svg className="w-4 h-4 text-slate-600 group-hover:text-slate-400 group-hover:translate-x-1 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </Link>
          ))}

          {/* Empty */}
          {!isLoading && jobs?.length === 0 && (
            <div className="px-5 py-16 text-center">
              <div className="text-5xl mb-4">📭</div>
              <p className="text-slate-400 font-medium mb-1">No validation jobs yet</p>
              <p className="text-slate-500 text-sm mb-4">Upload a CSV file to create your first job.</p>
              <Link href="/upload" className="btn-primary inline-flex items-center gap-2 text-sm">
                Get Started
              </Link>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
