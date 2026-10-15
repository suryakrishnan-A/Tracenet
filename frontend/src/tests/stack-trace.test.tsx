import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StackTraceViewer } from '@/components/StackTraceViewer';

describe('StackTraceViewer Component', () => {
  it('renders fallback when stack trace is null or empty', () => {
    render(<StackTraceViewer stackTrace={null} />);
    expect(screen.getByText(/No stack trace captured for this event/i)).toBeInTheDocument();
  });

  it('renders stack trace lines and copy button', () => {
    const trace = `Traceback (most recent call last):
  File "server.py", line 42, in handle_request
ValueError: Invalid payload received`;

    render(<StackTraceViewer stackTrace={trace} />);
    expect(screen.getByText(/Normalized Traceback/i)).toBeInTheDocument();
    expect(screen.getByText(/Invalid payload received/i)).toBeInTheDocument();
    expect(screen.getByText('Copy')).toBeInTheDocument();
  });
});
