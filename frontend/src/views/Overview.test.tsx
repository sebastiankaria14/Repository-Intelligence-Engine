import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import Overview from './Overview';
import { RepositoryProvider } from '../contexts/RepositoryContext';

describe('Overview', () => {
  test('renders NoRepository prompt when no repo is selected', () => {
    render(
      <MemoryRouter initialEntries={['/overview']}>
        <RepositoryProvider>
          <Overview />
        </RepositoryProvider>
      </MemoryRouter>,
    );

    expect(screen.getByText(/No repository selected/i)).toBeInTheDocument();
  });

  test('renders the page header', () => {
    render(
      <MemoryRouter initialEntries={['/overview']}>
        <RepositoryProvider>
          <Overview />
        </RepositoryProvider>
      </MemoryRouter>,
    );

    expect(screen.getByText(/Repository Overview/i)).toBeInTheDocument();
  });
});
