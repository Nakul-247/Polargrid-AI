import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import App from './App';
afterEach(() => { cleanup(); vi.useRealTimers(); });
describe('simulation UI states', () => {
  it('shows initial warning and validation data', () => { render(<App />); expect(screen.getAllByText('WARNING').length).toBeGreaterThan(0); expect(screen.getByText(/Prototype simulation using configurable assumptions/)).toBeTruthy(); expect(screen.getByText('Not run')).toBeTruthy(); });
  it('shows loading then completed state with populated dispatch charts', async () => { vi.useFakeTimers(); vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('offline'))); render(<App />); fireEvent.click(screen.getByText('Run Dispatch Simulation')); expect(screen.getByText('Solving…')).toBeTruthy(); await vi.advanceTimersByTimeAsync(900); expect(screen.getByText('Optimized just now')).toBeTruthy(); fireEvent.click(screen.getByText('Dispatch Plan')); expect(screen.getByText('Power balance · kW')).toBeTruthy(); expect(screen.getByText('Battery state of charge · %')).toBeTruthy(); });
  it('shows a clear fallback error state for generator failure', async () => { vi.useFakeTimers(); vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('offline'))); render(<App />); fireEvent.click(screen.getByText('Generator Failure')); fireEvent.click(screen.getByText('Run Dispatch Simulation')); await vi.advanceTimersByTimeAsync(900); expect(screen.getByText(/No feasible plan found under the selected constraints/)).toBeTruthy(); expect(screen.getByText('Emergency fallback')).toBeTruthy(); });
});

