'use client';

import React, { useState } from 'react';
import {
  Sparkles,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  FileSearch,
  Sliders,
  ShieldCheck,
  Cpu,
  Layers,
  ArrowRight,
  Info,
} from 'lucide-react';
import {
  InvestigationReportResponse,
  InvestigationStatus,
  AnalysisDepth,
  ConfidenceLevel,
} from '@/types';
import { investigateIssue } from '@/lib/api/issues';
import { ApiError } from '@/lib/api/client';

interface InvestigationPanelProps {
  issueId: string;
  onOpenKeyModal?: () => void;
}

export function InvestigationPanel({ issueId, onOpenKeyModal }: InvestigationPanelProps) {
  const [status, setStatus] = useState<InvestigationStatus>('idle');
  const [reportData, setReportData] = useState<InvestigationReportResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedDepth, setSelectedDepth] = useState<AnalysisDepth>('standard');

  const handleRunInvestigation = async () => {
    if (status === 'loading') return; // Prevent duplicate concurrent submissions

    setStatus('loading');
    setErrorMessage(null);

    try {
      const response = await investigateIssue(issueId, selectedDepth);
      setReportData(response);

      if (response.status === 'success') {
        setStatus('success');
      } else if (response.status === 'not_configured') {
        setStatus('not_configured');
      } else if (response.status === 'insufficient_evidence') {
        setStatus('insufficient_evidence');
      } else {
        setStatus('error');
        setErrorMessage(response.error_detail || 'Failed to complete incident analysis.');
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.isUnauthorized()) {
          setStatus('error');
          setErrorMessage('Project API key is missing or unauthorized (HTTP 401).');
        } else if (err.isNotFound()) {
          setStatus('error');
          setErrorMessage('Issue not found in this project (HTTP 404).');
        } else {
          setStatus('error');
          setErrorMessage(err.message);
        }
      } else {
        const msg = err instanceof Error ? err.message : 'Unknown network failure';
        setStatus('error');
        setErrorMessage(msg);
      }
    }
  };

  const getConfidenceBadge = (confidence: ConfidenceLevel) => {
    switch (confidence) {
      case 'high':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            High Confidence
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            Medium Confidence
          </span>
        );
      case 'low':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-800 text-slate-300 border border-slate-700">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
            Low Confidence
          </span>
        );
    }
  };

  const report = reportData?.report;

  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0d131f] overflow-hidden shadow-xl transition-all">
      {/* Top Banner / Section Header */}
      <div className="p-5 border-b border-slate-800/80 bg-gradient-to-r from-slate-950 via-[#0d131f] to-slate-950 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400 shadow-inner">
            <Sparkles className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-white tracking-tight">
                AI Incident Investigation Assistant
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                Phase 5 Evidence Grounded
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Automated root-cause hypothesis generation grounded strictly in collected error telemetry.
            </p>
          </div>
        </div>

        {/* Action Button & Depth Toggle */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          {status !== 'loading' && (
            <select
              value={selectedDepth}
              onChange={(e) => setSelectedDepth(e.target.value as AnalysisDepth)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300 focus:outline-none focus:border-blue-500"
              aria-label="Analysis Depth"
            >
              <option value="quick">Quick (Core)</option>
              <option value="standard">Standard</option>
              <option value="deep">Deep (Comprehensive)</option>
            </select>
          )}

          <button
            onClick={handleRunInvestigation}
            disabled={status === 'loading'}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium text-xs transition shadow-lg shadow-blue-600/25 active:scale-95"
          >
            <Sparkles className={`h-3.5 w-3.5 ${status === 'loading' ? 'animate-spin' : ''}`} />
            <span>
              {status === 'idle'
                ? 'Investigate with AI'
                : status === 'loading'
                ? 'Analyzing Evidence...'
                : 'Rerun Investigation'}
            </span>
          </button>
        </div>
      </div>

      {/* Main Body per State */}
      <div className="p-6">
        {/* 1. IDLE STATE */}
        {status === 'idle' && (
          <div className="py-8 px-4 text-center max-w-lg mx-auto space-y-4">
            <div className="h-12 w-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto text-blue-400">
              <Cpu className="h-6 w-6" />
            </div>
            <div className="space-y-1.5">
              <h4 className="text-sm font-semibold text-white">
                Initiate Evidence-Grounded Root Cause Analysis
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                TraceNest will construct an isolated evidence package from the normalized stack trace,
                endpoint response codes, and chronological occurrences to synthesize likely root causes.
              </p>
            </div>
            <div className="pt-2 flex flex-wrap items-center justify-center gap-3 text-[11px] font-mono text-slate-500">
              <span className="flex items-center gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-blue-400" />
                Prompt-Injection Isolated
              </span>
              <span>•</span>
              <span>Zero Fabricated Data</span>
              <span>•</span>
              <span>Scoped to Authorized Project</span>
            </div>
          </div>
        )}

        {/* 2. LOADING STATE */}
        {status === 'loading' && (
          <div className="py-12 px-4 text-center max-w-md mx-auto space-y-4 animate-in fade-in">
            <div className="relative mx-auto w-12 h-12">
              <div className="absolute inset-0 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
              <div className="absolute inset-2 rounded-full bg-blue-600/10 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-blue-400 animate-pulse" />
              </div>
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-white">Synthesizing Incident Evidence</h4>
              <p className="text-xs text-slate-400 leading-relaxed font-mono">
                Extracting call frames, correlating latency markers, and querying configured model...
              </p>
            </div>
          </div>
        )}

        {/* 3. NOT CONFIGURED STATE */}
        {status === 'not_configured' && (
          <div className="space-y-6">
            <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-amber-300">
                    AI Provider Not Configured (AI_API_KEY Missing)
                  </h4>
                  <p className="text-slate-300 text-[11px] mt-0.5">
                    Configure <code className="text-amber-200 font-mono">AI_API_KEY</code> in{' '}
                    <code className="text-amber-200 font-mono">backend/.env</code> to enable LLM model synthesis. Showing deterministic rule-based analysis below.
                  </p>
                </div>
              </div>
              <button
                onClick={handleRunInvestigation}
                className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs shrink-0 transition"
              >
                Retry
              </button>
            </div>

            {report && <ReportView report={report} reportData={reportData} />}
          </div>
        )}

        {/* 4. INSUFFICIENT EVIDENCE STATE */}
        {status === 'insufficient_evidence' && (
          <div className="py-8 px-4 text-center max-w-md mx-auto space-y-3">
            <HelpCircle className="h-10 w-10 text-amber-400 mx-auto" />
            <h4 className="text-sm font-semibold text-white">Insufficient Telemetry Evidence</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              This issue cluster contains zero associated telemetry event records. Ingest runtime error
              events to <code className="text-blue-400 font-mono">POST /api/v1/telemetry</code> to provide evidence for analysis.
            </p>
          </div>
        )}

        {/* 5. ERROR STATE */}
        {status === 'error' && (
          <div className="p-5 rounded-xl border border-rose-500/30 bg-rose-500/10 space-y-3">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-xs font-semibold text-rose-300">Investigation Error</h4>
                <p className="text-xs text-slate-300">{errorMessage || 'An error occurred during analysis.'}</p>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={handleRunInvestigation}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition"
              >
                <RefreshCw className="h-3 w-3" />
                <span>Retry Investigation</span>
              </button>

              {errorMessage && errorMessage.includes('401') && onOpenKeyModal && (
                <button
                  onClick={onOpenKeyModal}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition"
                >
                  Configure API Key
                </button>
              )}
            </div>
          </div>
        )}

        {/* 6. SUCCESS STATE */}
        {status === 'success' && report && (
          <ReportView report={report} reportData={reportData} />
        )}
      </div>
    </div>
  );
}

interface ReportViewProps {
  report: NonNullable<InvestigationReportResponse['report']>;
  reportData: InvestigationReportResponse | null;
}

function ReportView({ report, reportData }: ReportViewProps) {
  const getConfidenceBadge = (confidence: ConfidenceLevel) => {
    switch (confidence) {
      case 'high':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            High Confidence
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            Medium Confidence
          </span>
        );
      case 'low':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-800 text-slate-300 border border-slate-700">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
            Low Confidence
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Meta Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800 text-xs font-mono text-slate-400">
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Provider:</span>
          <span className="text-blue-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            {reportData?.provider || 'LLM Engine'} ({reportData?.model})
          </span>
          {reportData?.is_ai_generated ? (
            <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 text-[10px]">
              AI Synthesized
            </span>
          ) : (
            <span className="text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 text-[10px]">
              Deterministic Analysis
            </span>
          )}
        </div>

        <div className="text-[11px] text-slate-500">
          Generated: {reportData?.generated_at ? new Date(reportData.generated_at).toLocaleTimeString() : 'now'}
        </div>
      </div>

      {/* A. Executive Summary */}
      <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-5 space-y-3">
        <div className="flex items-center gap-2 text-xs font-mono font-semibold uppercase tracking-wider text-blue-400">
          <FileSearch className="h-4 w-4" />
          <span>A. Executive Summary</span>
        </div>

        <p className="text-sm font-semibold text-white leading-relaxed">
          {report.executive_summary.summary}
        </p>

        {report.executive_summary.affected_component && (
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-500">Affected Component:</span>
            <span className="text-slate-200 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              {report.executive_summary.affected_component}
            </span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs">
          <div className="p-3 rounded-lg bg-[#070b14] border border-slate-800/80 space-y-1">
            <span className="text-[10px] font-mono uppercase text-slate-500">Evidence Synthesis</span>
            <p className="text-slate-300 leading-relaxed">{report.executive_summary.evidence_synthesis}</p>
          </div>
          <div className="p-3 rounded-lg bg-[#070b14] border border-slate-800/80 space-y-1">
            <span className="text-[10px] font-mono uppercase text-slate-500">Certainty Assessment</span>
            <p className="text-slate-300 leading-relaxed">{report.executive_summary.certainty_assessment}</p>
          </div>
        </div>
      </div>

      {/* B. Observed Facts */}
      <div className="space-y-3">
        <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <span>B. Observed Facts Directly Supported by Telemetry ({report.observed_facts.length})</span>
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          {report.observed_facts.map((fact, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 text-xs flex items-start justify-between gap-3"
            >
              <div className="space-y-1">
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 uppercase">
                  {fact.category}
                </span>
                <p className="text-slate-200 leading-relaxed mt-1">{fact.fact}</p>
              </div>

              {fact.evidence_reference && (
                <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 shrink-0">
                  {fact.evidence_reference}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* C. Likely Causes */}
      <div className="space-y-3">
        <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Layers className="h-4 w-4 text-purple-400" />
          <span>C. Ranked Hypotheses & Plausible Causes</span>
        </h4>

        <div className="space-y-3">
          {report.likely_causes.map((cause) => (
            <div
              key={cause.rank}
              className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <span className="h-6 w-6 rounded-md bg-blue-600/20 border border-blue-500/30 text-blue-400 font-mono text-xs flex items-center justify-center font-bold">
                    #{cause.rank}
                  </span>
                  <h5 className="text-sm font-semibold text-white">{cause.title}</h5>
                </div>
                {getConfidenceBadge(cause.confidence)}
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">{cause.explanation}</p>

              <div className="p-3 rounded-lg bg-[#070b14] border border-slate-800 text-xs space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] text-slate-500 font-mono">Supporting Evidence:</span>
                  {cause.supporting_evidence.length > 0 ? (
                    cause.supporting_evidence.map((ref, rIdx) => (
                      <span
                        key={rIdx}
                        className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20"
                      >
                        {ref}
                      </span>
                    ))
                  ) : (
                    <span className="text-[11px] text-slate-500 italic">Grounded in error signature</span>
                  )}
                </div>

                <div className="text-[11px] text-slate-400">
                  <strong className="text-slate-300">Rationale: </strong>
                  {cause.plausibility_rationale}
                </div>

                {cause.missing_or_contradictory_evidence && (
                  <div className="text-[11px] text-amber-300/90 pt-1 border-t border-slate-800/80">
                    <strong className="text-amber-400">Uncertainty & Missing Data: </strong>
                    {cause.missing_or_contradictory_evidence}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* D. Recommended Debugging Steps */}
      <div className="space-y-3">
        <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Sliders className="h-4 w-4 text-blue-400" />
          <span>D. Prioritized Actionable Debugging Steps</span>
        </h4>

        <div className="space-y-2">
          {report.recommended_steps.map((step) => (
            <div
              key={step.priority}
              className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 flex items-start gap-3 text-xs"
            >
              <span className="h-5 w-5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[11px] flex items-center justify-center shrink-0 mt-0.5">
                {step.priority}
              </span>

              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                    {step.step_type.replace('_', ' ')}
                  </span>
                  {step.target && (
                    <code className="text-[11px] font-mono text-blue-400 bg-blue-500/10 px-1.5 rounded">
                      {step.target}
                    </code>
                  )}
                </div>
                <p className="text-slate-200 leading-relaxed">{step.action}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* E. Missing Evidence & Limitations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Missing Evidence */}
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4 space-y-2">
          <h5 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <HelpCircle className="h-3.5 w-3.5 text-amber-400" />
            <span>E. Additional Evidence Needed</span>
          </h5>
          {report.missing_evidence.length > 0 ? (
            <ul className="text-xs text-slate-300 space-y-1.5 list-disc list-inside">
              {report.missing_evidence.map((item, idx) => (
                <li key={idx} className="leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500 italic">Sufficient incident telemetry provided for initial triage.</p>
          )}
        </div>

        {/* F. Limitations & Security Disclaimer */}
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4 space-y-2">
          <h5 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Info className="h-3.5 w-3.5 text-blue-400" />
            <span>F. Investigation Boundaries & Security</span>
          </h5>
          <p className="text-xs text-slate-300 leading-relaxed">{report.limitations}</p>
          <div className="pt-2 border-t border-slate-800/60 text-[11px] text-slate-500 leading-relaxed">
            Telemetry evidence was sanitized before model transmission. The model operates in read-only analysis without shell, database, or filesystem execution capabilities.
          </div>
        </div>
      </div>
    </div>
  );
}
