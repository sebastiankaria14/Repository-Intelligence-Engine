import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import { ErrorBoundary } from './components/ErrorBoundary';
import { RepositoryModal } from './components/RepositoryModal';
import Overview from './views/Overview';
import Architecture from './views/Architecture';
import APIExplorer from './views/APIExplorer';
import DatabaseExplorer from './views/DatabaseExplorer';
import DependencyExplorer from './views/DependencyExplorer';
import GitInsights from './views/GitInsights';
import GraphExplorer from './views/GraphExplorer';
import Chat from './views/Chat';
import Landing from './views/Landing';
import { RepositoryProvider } from './contexts/RepositoryContext';
import { ModalProvider, useModal } from './contexts/ModalContext';
import { repositoryApi } from './lib/api';
import { useRepositoryContext } from './contexts/useRepositoryContext';
import './index.css';

function AppLayout() {
  const { isRepositoryModalOpen, closeRepositoryModal } = useModal();
  const { setRepo } = useRepositoryContext();

  const handleAddRepo = async (url: string) => {
    try {
      const { data } = await repositoryApi.create({ github_url: url.trim() });
      setRepo(data);
    } catch (err) {
      console.error('Failed to add repository:', err);
      throw err;
    }
  };

  return (
    <>
      <div className="flex flex-col h-screen overflow-hidden bg-[#0d0f12] text-gray-100">
        <Header />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto px-8 py-8 lg:px-10">
            <div className="max-w-[1400px] mx-auto">
              <Routes>
                <Route path="/" element={<Navigate to="/overview" replace />} />
                <Route path="/overview" element={<Overview />} />
                <Route path="/architecture" element={<Architecture />} />
                <Route path="/apis" element={<APIExplorer />} />
                <Route path="/database" element={<DatabaseExplorer />} />
                <Route path="/dependencies" element={<DependencyExplorer />} />
                <Route path="/git" element={<GitInsights />} />
                <Route path="/graph" element={<GraphExplorer />} />
                <Route path="/chat" element={<Chat />} />
              </Routes>
            </div>
          </main>
        </div>
      </div>

      {/* Global Repository Modal */}
      <RepositoryModal
        isOpen={isRepositoryModalOpen}
        onClose={closeRepositoryModal}
        onSubmit={handleAddRepo}
      />
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/start" element={<Landing />} />
          <Route
            path="/*"
            element={
              <RepositoryProvider>
                <ModalProvider>
                  <AppLayout />
                </ModalProvider>
              </RepositoryProvider>
            }
          />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
