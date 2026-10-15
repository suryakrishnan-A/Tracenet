'use client';

import React, { useState } from 'react';
import { Key, PlusCircle, CheckCircle, AlertCircle, X, Shield, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { ProjectResponse } from '@/types';

interface ApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onKeyChanged: (newKey: string | null) => void;
}

export function ApiKeyModal({ isOpen, onClose, onKeyChanged }: ApiKeyModalProps) {
  const currentKey = apiClient.getApiKey();
  const [inputKey, setInputKey] = useState(currentKey || '');
  const [newProjectName, setNewProjectName] = useState('Local Dev Service');
  const [isRegistering, setIsRegistering] = useState(false);
  const [createdProject, setCreatedProject] = useState<ProjectResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSaveManualKey = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanKey = inputKey.trim();
    if (!cleanKey) {
      setError('Please provide a valid API key (e.g. tn_live_...)');
      return;
    }
    apiClient.setApiKey(cleanKey);
    setError(null);
    onKeyChanged(cleanKey);
    onClose();
  };

  const handleRegisterProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) {
      setError('Project name cannot be empty');
      return;
    }
    setIsRegistering(true);
    setError(null);
    try {
      const resp = await apiClient.registerProject(newProjectName.trim());
      setCreatedProject(resp);
      setInputKey(resp.api_key);
      apiClient.setApiKey(resp.api_key);
      onKeyChanged(resp.api_key);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to register project';
      setError(msg);
    } finally {
      setIsRegistering(false);
    }
  };

  const handleClearKey = () => {
    apiClient.setApiKey(null);
    setInputKey('');
    setCreatedProject(null);
    onKeyChanged(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-[#0c121e] shadow-2xl p-6 space-y-6 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Key className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Project API Key Management</h2>
              <p className="text-xs text-slate-400">Authenticate requests for your monitored service</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-xs text-rose-300 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {createdProject ? (
          <div className="space-y-4">
            <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 space-y-3">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs uppercase tracking-wider">
                <CheckCircle className="h-4 w-4" />
                Project Registered Successfully
              </div>
              <p className="text-xs text-slate-300">
                Created project <strong className="text-white">{createdProject.name}</strong>. The raw API key has been activated in your session.
              </p>
              <div className="p-2.5 rounded bg-slate-950 font-mono text-xs text-emerald-300 break-all border border-slate-800 select-all">
                {createdProject.api_key}
              </div>
              <p className="text-[11px] text-amber-300 font-medium">
                ⚠️ Store this key securely. The backend only stores a SHA-256 hash and cannot reveal it again.
              </p>
            </div>

            <button
              onClick={onClose}
              className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs transition"
            >
              Done & Return to Dashboard
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Existing Key Input */}
            <form onSubmit={handleSaveManualKey} className="space-y-3">
              <label className="block text-xs font-medium text-slate-300">
                Use Existing API Key
              </label>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={inputKey}
                  onChange={(e) => setInputKey(e.target.value)}
                  placeholder="tn_live_..."
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition"
                >
                  Save Key
                </button>
              </div>
              <p className="text-[11px] text-slate-500">
                Stored locally in browser <code className="text-slate-400">localStorage</code> for this session.
              </p>
            </form>

            <div className="relative flex py-1 items-center">
              <div className="flex-grow border-t border-slate-800" />
              <span className="flex-shrink mx-3 text-slate-500 text-[10px] uppercase font-mono tracking-widest">
                or generate new
              </span>
              <div className="flex-grow border-t border-slate-800" />
            </div>

            {/* Quick Project Creation Form */}
            <form onSubmit={handleRegisterProject} className="space-y-3">
              <label className="block text-xs font-medium text-slate-300">
                Register New Local Dev Project
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="e.g. Checkout Service"
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="submit"
                  disabled={isRegistering}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white text-xs font-medium transition"
                >
                  {isRegistering ? (
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <PlusCircle className="h-3.5 w-3.5 text-blue-400" />
                  )}
                  Create
                </button>
              </div>
            </form>

            {currentKey && (
              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-slate-400">Current Key configured</span>
                <button
                  type="button"
                  onClick={handleClearKey}
                  className="text-rose-400 hover:text-rose-300 font-medium"
                >
                  Clear Key
                </button>
              </div>
            )}
          </div>
        )}

        <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/60 flex items-start gap-2.5 text-[11px] text-slate-500 leading-relaxed">
          <Shield className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
          <span>
            API keys are transmitted securely via the <code className="text-slate-400 font-mono">X-API-Key</code> header to your local FastAPI backend ({apiClient.getBaseUrl()}). Keys are never transmitted to third parties.
          </span>
        </div>
      </div>
    </div>
  );
}
