import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SeverityBadge } from '@/components/SeverityBadge';
import { StatusBadge } from '@/components/StatusBadge';

describe('SeverityBadge Component', () => {
  it('renders critical severity badge correctly', () => {
    render(<SeverityBadge severity="critical" />);
    expect(screen.getByText('critical')).toBeInTheDocument();
  });

  it('renders warning severity badge correctly', () => {
    render(<SeverityBadge severity="warning" />);
    expect(screen.getByText('warning')).toBeInTheDocument();
  });

  it('renders fallback for unexpected severity', () => {
    render(<SeverityBadge severity="unknown_sev" />);
    expect(screen.getByText('unknown_sev')).toBeInTheDocument();
  });
});

describe('StatusBadge Component', () => {
  it('renders unresolved status correctly', () => {
    render(<StatusBadge status="unresolved" />);
    expect(screen.getByText('Unresolved')).toBeInTheDocument();
  });

  it('renders investigating status correctly', () => {
    render(<StatusBadge status="investigating" />);
    expect(screen.getByText('Investigating')).toBeInTheDocument();
  });

  it('renders resolved status correctly', () => {
    render(<StatusBadge status="resolved" />);
    expect(screen.getByText('Resolved')).toBeInTheDocument();
  });

  it('renders ignored status correctly', () => {
    render(<StatusBadge status="ignored" />);
    expect(screen.getByText('Ignored')).toBeInTheDocument();
  });
});
