import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConflictWarningBanner, type ConstraintConflict } from '../ConflictWarningBanner';

describe('ConflictWarningBanner', () => {
  const mockConflicts: ConstraintConflict[] = [
    {
      type: 'error',
      code: 'CONTRIBUTION_MIN_EXCEEDS_100',
      message: 'Sum of minimum contributions exceeds 100%',
      affected_variables: ['tv_spend', 'digital_spend'],
      affected_groups: [],
      suggestion: 'Reduce minimum contribution percentages',
    },
    {
      type: 'warning',
      code: 'VARIABLE_IN_MULTIPLE_GROUPS',
      message: 'Variable appears in multiple groups',
      affected_variables: ['tv_spend'],
      affected_groups: ['offline', 'traditional'],
      suggestion: 'Consider removing from one group',
    },
    {
      type: 'info',
      code: 'POSITIVE_SIGN_OVERRIDES_NEGATIVE_MIN',
      message: 'Positive sign will override negative min',
      affected_variables: ['radio_spend'],
      affected_groups: [],
      suggestion: null,
    },
  ];

  it('renders nothing when conflicts array is empty', () => {
    const { container } = render(<ConflictWarningBanner conflicts={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders all conflict messages', () => {
    render(<ConflictWarningBanner conflicts={mockConflicts} />);
    
    expect(screen.getByText('Sum of minimum contributions exceeds 100%')).toBeInTheDocument();
    expect(screen.getByText('Variable appears in multiple groups')).toBeInTheDocument();
    expect(screen.getByText('Positive sign will override negative min')).toBeInTheDocument();
  });

  it('displays affected variables', () => {
    render(<ConflictWarningBanner conflicts={mockConflicts} />);
    
    expect(screen.getByText(/tv_spend, digital_spend/)).toBeInTheDocument();
  });

  it('displays affected groups', () => {
    render(<ConflictWarningBanner conflicts={mockConflicts} />);
    
    expect(screen.getByText(/offline, traditional/)).toBeInTheDocument();
  });

  it('displays suggestions when available', () => {
    render(<ConflictWarningBanner conflicts={mockConflicts} />);
    
    expect(screen.getByText(/Reduce minimum contribution percentages/)).toBeInTheDocument();
    expect(screen.getByText(/Consider removing from one group/)).toBeInTheDocument();
  });

  it('shows error count in summary', () => {
    render(<ConflictWarningBanner conflicts={mockConflicts} />);
    
    // Should show error count (1 error)
    expect(screen.getByText('constraints.errorsCount')).toBeInTheDocument();
  });

  it('shows warning count in summary', () => {
    render(<ConflictWarningBanner conflicts={mockConflicts} />);
    
    // Should show warning count (1 warning)
    expect(screen.getByText('constraints.warningsCount')).toBeInTheDocument();
  });

  it('calls onDismiss when dismiss button is clicked', () => {
    const onDismiss = vi.fn();
    render(<ConflictWarningBanner conflicts={mockConflicts} onDismiss={onDismiss} />);
    
    // Find all dismiss buttons (X icons)
    const dismissButtons = screen.getAllByRole('button');
    
    // Click the first dismiss button
    fireEvent.click(dismissButtons[0]);
    
    expect(onDismiss).toHaveBeenCalledWith(0);
  });

  it('does not show dismiss buttons when onDismiss is not provided', () => {
    render(<ConflictWarningBanner conflicts={mockConflicts} />);
    
    // Should not have any buttons when onDismiss is not provided
    const buttons = screen.queryAllByRole('button');
    expect(buttons.length).toBe(0);
  });

  it('applies custom className', () => {
    const { container } = render(
      <ConflictWarningBanner conflicts={mockConflicts} className="custom-class" />
    );
    
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('renders only errors when there are no warnings', () => {
    const errorsOnly: ConstraintConflict[] = [
      {
        type: 'error',
        code: 'ERROR_1',
        message: 'Error message 1',
        affected_variables: [],
        affected_groups: [],
        suggestion: null,
      },
      {
        type: 'error',
        code: 'ERROR_2',
        message: 'Error message 2',
        affected_variables: [],
        affected_groups: [],
        suggestion: null,
      },
    ];

    render(<ConflictWarningBanner conflicts={errorsOnly} />);
    
    expect(screen.getByText('Error message 1')).toBeInTheDocument();
    expect(screen.getByText('Error message 2')).toBeInTheDocument();
  });

  it('renders only warnings when there are no errors', () => {
    const warningsOnly: ConstraintConflict[] = [
      {
        type: 'warning',
        code: 'WARNING_1',
        message: 'Warning message 1',
        affected_variables: [],
        affected_groups: [],
        suggestion: null,
      },
    ];

    render(<ConflictWarningBanner conflicts={warningsOnly} />);
    
    expect(screen.getByText('Warning message 1')).toBeInTheDocument();
  });

  it('renders info messages last', () => {
    const mixedConflicts: ConstraintConflict[] = [
      { type: 'info', code: 'I1', message: 'Info first in array', affected_variables: [], affected_groups: [], suggestion: null },
      { type: 'error', code: 'E1', message: 'Error message', affected_variables: [], affected_groups: [], suggestion: null },
      { type: 'warning', code: 'W1', message: 'Warning message', affected_variables: [], affected_groups: [], suggestion: null },
    ];

    render(<ConflictWarningBanner conflicts={mixedConflicts} />);
    
    // All messages should be rendered
    expect(screen.getByText('Info first in array')).toBeInTheDocument();
    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.getByText('Warning message')).toBeInTheDocument();
  });
});
