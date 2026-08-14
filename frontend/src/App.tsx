import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import { ErrorBoundary } from './components/ErrorBoundary';
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
import './index.css';

function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto px-6 py-6 lg:px-8">
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
                <AppLayout />
              </RepositoryProvider>
            }
          />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
