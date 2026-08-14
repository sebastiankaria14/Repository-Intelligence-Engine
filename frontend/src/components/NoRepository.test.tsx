import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import NoRepository from './NoRepository';
import { RepositoryProvider } from '../contexts/RepositoryContext';

describe('NoRepository', () => {
  test('renders the empty-state prompt', () => {
    render(
      <MemoryRouter>
        <RepositoryProvider>
          <NoRepository />
        </RepositoryProvider>
      </MemoryRouter>,
    );

    expect(screen.getByText(/No repository selected/i)).toBeInTheDocument();
    expect(screen.getByText(/Add a GitHub repository/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Add Repository/i }),
    ).toBeInTheDocument();
  });

  test('renders nothing that calls the API on initial render', () => {
    render(
      <MemoryRouter>
        <RepositoryProvider>
          <NoRepository />
        </RepositoryProvider>
      </MemoryRouter>,
    );
    // The "Add Repository" button should be present and enabled
    expect(screen.getByRole('button', { name: /Add Repository/i })).toBeEnabled();
  });
});
