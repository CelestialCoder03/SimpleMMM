import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { VariableGroupManager } from '../VariableGroupManager';

// Mock the API
vi.mock('@/api/services/variableGroups', () => ({
  variableGroupsApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    checkOverlap: vi.fn(),
  },
}));

import { variableGroupsApi } from '@/api/services/variableGroups';

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

describe('VariableGroupManager', () => {
  const mockProjectId = 'test-project-id';
  const mockVariables = ['tv_spend', 'digital_spend', 'radio_spend', 'print_spend'];

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock implementations
    (variableGroupsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (variableGroupsApi.checkOverlap as ReturnType<typeof vi.fn>).mockResolvedValue({
      has_overlaps: false,
      overlaps: {},
    });
  });

  it('renders the component with title', async () => {
    renderWithProviders(
      <VariableGroupManager
        projectId={mockProjectId}
        availableVariables={mockVariables}
      />
    );

    expect(screen.getByText('variableGroups.title')).toBeInTheDocument();
  });

  it('shows empty state when no groups exist', async () => {
    renderWithProviders(
      <VariableGroupManager
        projectId={mockProjectId}
        availableVariables={mockVariables}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('variableGroups.noGroups')).toBeInTheDocument();
    });
  });

  it('displays existing groups', async () => {
    const mockGroups = [
      {
        id: 'group-1',
        name: 'Offline Media',
        description: 'Traditional channels',
        variables: ['tv_spend', 'radio_spend'],
        color: '#3B82F6',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ];

    (variableGroupsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue(mockGroups);

    renderWithProviders(
      <VariableGroupManager
        projectId={mockProjectId}
        availableVariables={mockVariables}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Offline Media')).toBeInTheDocument();
    });
  });

  it('opens create dialog when clicking create button', async () => {
    renderWithProviders(
      <VariableGroupManager
        projectId={mockProjectId}
        availableVariables={mockVariables}
      />
    );

    const createButton = screen.getByText('variableGroups.createGroup');
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(screen.getByText('variableGroups.groupName')).toBeInTheDocument();
    });
  });

  it('shows variable checkboxes in create dialog', async () => {
    renderWithProviders(
      <VariableGroupManager
        projectId={mockProjectId}
        availableVariables={mockVariables}
      />
    );

    const createButton = screen.getByText('variableGroups.createGroup');
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(screen.getByText('tv_spend')).toBeInTheDocument();
      expect(screen.getByText('digital_spend')).toBeInTheDocument();
    });
  });

  it('shows color picker in create dialog', async () => {
    renderWithProviders(
      <VariableGroupManager
        projectId={mockProjectId}
        availableVariables={mockVariables}
      />
    );

    const createButton = screen.getByText('variableGroups.createGroup');
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(screen.getByText('variableGroups.color')).toBeInTheDocument();
    });
  });

  it('calls create API when submitting new group', async () => {
    const user = userEvent.setup();
    
    (variableGroupsApi.create as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'new-group-id',
      name: 'New Group',
      variables: ['tv_spend'],
      color: '#3B82F6',
    });

    renderWithProviders(
      <VariableGroupManager
        projectId={mockProjectId}
        availableVariables={mockVariables}
      />
    );

    // Open dialog
    const createButton = screen.getByText('variableGroups.createGroup');
    fireEvent.click(createButton);

    // Fill in name
    await waitFor(() => {
      expect(screen.getByPlaceholderText('variableGroups.groupNamePlaceholder')).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText('variableGroups.groupNamePlaceholder');
    await user.type(nameInput, 'New Group');

    // Select a variable
    const checkbox = screen.getByText('tv_spend').closest('label')?.querySelector('input');
    if (checkbox) {
      await user.click(checkbox);
    }

    // Submit - find the submit button (second "Create Group" button in the dialog)
    const buttons = screen.getAllByText('variableGroups.createGroup');
    const submitButton = buttons[buttons.length - 1];
    await user.click(submitButton);

    await waitFor(() => {
      expect(variableGroupsApi.create).toHaveBeenCalledWith(
        mockProjectId,
        expect.objectContaining({
          name: 'New Group',
          variables: ['tv_spend'],
        })
      );
    });
  });

  it('shows overlap warning when variables are in multiple groups', async () => {
    const mockGroups = [
      {
        id: 'group-1',
        name: 'Group A',
        variables: ['tv_spend'],
        color: '#3B82F6',
      },
      {
        id: 'group-2',
        name: 'Group B',
        variables: ['tv_spend'],
        color: '#10B981',
      },
    ];

    (variableGroupsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue(mockGroups);
    (variableGroupsApi.checkOverlap as ReturnType<typeof vi.fn>).mockResolvedValue({
      has_overlaps: true,
      overlaps: {
        tv_spend: ['Group A', 'Group B'],
      },
    });

    renderWithProviders(
      <VariableGroupManager
        projectId={mockProjectId}
        availableVariables={mockVariables}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('variableGroups.overlapWarning')).toBeInTheDocument();
    });
  });

  it('calls delete API when deleting a group', async () => {
    const mockGroups = [
      {
        id: 'group-to-delete',
        name: 'Delete Me',
        variables: ['tv_spend'],
        color: '#3B82F6',
      },
    ];

    (variableGroupsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue(mockGroups);
    (variableGroupsApi.delete as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);

    // Mock window.confirm
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    renderWithProviders(
      <VariableGroupManager
        projectId={mockProjectId}
        availableVariables={mockVariables}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Delete Me')).toBeInTheDocument();
    });

    // Find and click delete button (trash icon button)
    const deleteButtons = screen.getAllByRole('button');
    const deleteButton = deleteButtons.find((btn: HTMLElement) =>
      btn.querySelector('svg.lucide-trash-2')
    );

    if (deleteButton) {
      fireEvent.click(deleteButton);
    }

    await waitFor(() => {
      expect(variableGroupsApi.delete).toHaveBeenCalledWith(
        mockProjectId,
        'group-to-delete'
      );
    });
  });

  it('shows member count for each group', async () => {
    const mockGroups = [
      {
        id: 'group-1',
        name: 'Media Group',
        variables: ['tv_spend', 'radio_spend', 'print_spend'],
        color: '#3B82F6',
      },
    ];

    (variableGroupsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue(mockGroups);

    renderWithProviders(
      <VariableGroupManager
        projectId={mockProjectId}
        availableVariables={mockVariables}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/variableGroups.members.*3/)).toBeInTheDocument();
    });
  });
});
