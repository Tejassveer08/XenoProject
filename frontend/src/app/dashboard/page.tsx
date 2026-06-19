'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import Nav from '@/components/Nav';

export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    if (!localStorage.getItem('token')) router.replace('/login');
  }, [router]);

  const { data: user } = useQuery({ queryKey: ['me'], queryFn: api.me });
  const { data: jobs } = useQuery({ queryKey: ['jobs'], queryFn: api.listValidationJobs });

  const totalJobs = jobs?.length ?? 0;
  const completedJobs = jobs?.filter((j) => j.status === 'SUCCEEDED').length ?? 0;
  const inProgressJobs = jobs?.filter((j) => j.status === 'RUNNING' || j.status === 'PENDING').length ?? 0;
  const failedJobs = jobs?.filter((j) => j.status === 'FAILED').length ?? 0;

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8 animate-fade-in-up">
          <h1 className="text-3xl font-bold text-white mb-1">
            Welcome back{user ? ',' : ''}
            {user && <span className="gradient-text ml-2">{user.email.split('@')[0]}</span>}
          </h1>
          <p className="text-slate-400">Here&apos;s an overview of your validation activity.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            label="Total Jobs"
            value={totalJobs}
            icon="📊"
            gradient="from-brand-500/20 to-purple-500/20"
            textColor="text-brand-400"
            delay="stagger-1"
          />
          <StatCard
            label="Completed"
            value={completedJobs}
            icon="✅"
            gradient="from-emerald-500/20 to-green-500/20"
            textColor="text-emerald-400"
            delay="stagger-2"
          />
          <StatCard
            label="In Progress"
            value={inProgressJobs}
            icon="⚡"
            gradient="from-amber-500/20 to-orange-500/20"
            textColor="text-amber-400"
            delay="stagger-3"
          />
          <StatCard
            label="Failed"
            value={failedJobs}
            icon="⚠️"
            gradient="from-red-500/20 to-pink-500/20"
            textColor="text-red-400"
            delay="stagger-4"
          />
        </div>

        {/* Quick Start + Recent Activity */}
        <div className="grid lg:grid-cols-5 gap-6">
          {/* Quick Start */}
          <div className="lg:col-span-2 glass-card p-6 animate-fade-in-up stagger-3" style={{ animationFillMode: 'both' }}>
            <h2 className="font-semibold text-white text-lg mb-4 flex items-center gap-2">
              <span className="text-xl">🚀</span> Quick Start
            </h2>
            <ol className="space-y-3">
              {[
                { step: '1', text: 'Upload a CSV file with transaction data', icon: '📁' },
                { step: '2', text: 'Select dataset type and validation rules', icon: '⚙️' },
                { step: '3', text: 'Download cleaned output & error reports', icon: '📥' },
              ].map((item) => (
                <li key={item.step} className="flex items-start gap-3 text-slate-300 text-sm">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center text-xs font-bold">
                    {item.step}
                  </span>
                  <span>{item.text}</span>
                </li>
              ))}
            </ol>
            <Link href="/upload" className="btn-primary mt-6 inline-flex items-center gap-2 text-sm">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Upload &amp; Validate
            </Link>
          </div>

          {/* Recent Jobs */}
          <div className="lg:col-span-3 glass-card p-6 animate-fade-in-up stagger-4" style={{ animationFillMode: 'both' }}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-white text-lg flex items-center gap-2">
                <span className="text-xl">📋</span> Recent Jobs
              </h2>
              <Link href="/jobs" className="text-sm text-brand-400 hover:text-brand-300 transition-colors">
                View all →
              </Link>
            </div>
            {!jobs || jobs.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <div className="text-4xl mb-2">📭</div>
                <p className="text-sm">No validation jobs yet. Upload a file to get started!</p>
              </div>
            ) : (
              <div className="space-y-2">
                {jobs.slice(0, 5).map((job) => (
                  <Link
                    key={job.id}
                    href={`/jobs/${job.id}`}
                    className="flex items-center justify-between p-3 rounded-xl hover:bg-white/[0.04] transition-all duration-200 group"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-slate-500">{job.id.slice(0, 8)}</span>
                      <span className="text-sm text-slate-300 capitalize">{job.dataset_type}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge status={job.status} />
                      <svg className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* API Key */}
        {user?.api_key && (
          <div className="mt-6 glass-card p-5 animate-fade-in-up">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm">🔑</span>
              <span className="font-medium text-white text-sm">API Key</span>
              <span className="text-xs text-slate-500">(for integrations)</span>
            </div>
            <code className="block text-xs font-mono text-brand-400 bg-white/[0.04] p-3 rounded-lg break-all">
              {user.api_key}
            </code>
          </div>
        )}
      </main>
    </div>
  );
}

function StatCard({ label, value, icon, gradient, textColor, delay }: {
  label: string;
  value: number;
  icon: string;
  gradient: string;
  textColor: string;
  delay: string;
}) {
  return (
    <div className={`glass-card-hover p-5 animate-fade-in-up ${delay}`} style={{ animationFillMode: 'both' }}>
      <div className={`inline-flex w-10 h-10 rounded-xl bg-gradient-to-br ${gradient} items-center justify-center text-lg mb-3`}>
        {icon}
      </div>
      <div className={`text-3xl font-bold ${textColor}`}>{value}</div>
      <div className="text-sm text-slate-400 mt-1">{label}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    SUCCEEDED: 'status-succeeded',
    FAILED: 'status-failed',
    RUNNING: 'status-running',
    PENDING: 'status-pending',
  };
  return (
    <span className={`status-badge ${styles[status] || styles.PENDING}`}>
      {status}
    </span>
  );
}
