import React, { useState, useEffect } from 'react';
import {
  HealthData,
  DashboardOverviewResponse,
  Product,
  Source,
  TrendMetric,
} from './types';
import { api } from './services/api';
import { Header } from './components/layout/Header';
import { Navbar, TabKey } from './components/layout/Navbar';
import { OverviewView } from './components/views/OverviewView';
import { ReviewExplorerView } from './components/views/ReviewExplorerView';
import { ClustersView } from './components/views/ClustersView';
import { RecommendationsView } from './components/views/RecommendationsView';
import { ReportsView } from './components/views/ReportsView';
import { RoutingMatrixView } from './components/views/RoutingMatrixView';
import { CAPITAL_ONE_CATALOG } from './constants/catalog';
import { NeuralBackground } from './components/common/NeuralBackground';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [health, setHealth] = useState<HealthData | null>(null);
  const [overview, setOverview] = useState<DashboardOverviewResponse | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [trends, setTrends] = useState<TrendMetric[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedClusterForInvestigation, setSelectedClusterForInvestigation] = useState<string | undefined>(undefined);

  const loadGlobalData = async () => {
    setLoading(true);
    try {
      const [healthData, overviewData, productsData, sourcesData, trendsData] =
        await Promise.allSettled([
          api.getHealth(),
          api.getOverview(),
          api.getProducts(),
          api.getSources(),
          api.getTrends(undefined, 1, 10),
        ]);

      if (healthData.status === 'fulfilled') setHealth(healthData.value);
      if (overviewData.status === 'fulfilled') setOverview(overviewData.value);
      if (productsData.status === 'fulfilled' && productsData.value.length > 0) {
        setProducts(productsData.value);
      } else {
        setProducts(
          CAPITAL_ONE_CATALOG.map((c) => ({
            id: c.id,
            name: c.name,
            family: c.family,
            description: c.description,
          }))
        );
      }

      if (sourcesData.status === 'fulfilled') setSources(sourcesData.value);
      if (trendsData.status === 'fulfilled') setTrends(trendsData.value.items);
    } catch (err) {
      console.error('Failed to load global dashboard state:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGlobalData();
  }, []);

  const handleTriggerClustering = async () => {
    setLoading(true);
    try {
      await api.runClustering(0.4, 3);
      await api.calculateTrends();
      await loadGlobalData();
    } catch (err: any) {
      alert(`Clustering failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerTrends = async () => {
    setLoading(true);
    try {
      await api.calculateTrends();
      await loadGlobalData();
    } catch (err: any) {
      alert(`Recalculate trends failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleNavigateToInvestigation = (clusterId: string) => {
    setSelectedClusterForInvestigation(clusterId);
    setActiveTab('recommendations');
  };

  return (
    <div className="min-h-screen bg-[#040B16] text-slate-100 flex flex-col font-sans selection:bg-sky-500 selection:text-white relative overflow-x-hidden cyber-grid-bg">
      {/* Interactive 3D Neural Constellation Mesh Canvas */}
      <NeuralBackground />

      {/* Header with real-time status */}
      <Header health={health} loading={loading} onRefresh={loadGlobalData} />

      {/* Navigation tabs */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        pendingRecsCount={overview?.pending_recommendations_count}
        anomaliesCount={overview?.anomalies_count}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 relative z-10">
        {activeTab === 'overview' && (
          <OverviewView
            overview={overview}
            trends={trends}
            onNavigateTab={setActiveTab}
            onTriggerClustering={handleTriggerClustering}
            onTriggerTrends={handleTriggerTrends}
          />
        )}

        {activeTab === 'reviews' && (
          <ReviewExplorerView
            products={products}
            sources={sources}
            onReviewIngested={loadGlobalData}
          />
        )}

        {activeTab === 'clusters' && (
          <ClustersView
            onNavigateToInvestigation={handleNavigateToInvestigation}
          />
        )}

        {activeTab === 'recommendations' && (
          <RecommendationsView
            initialClusterId={selectedClusterForInvestigation}
          />
        )}

        {activeTab === 'reports' && <ReportsView />}

        {activeTab === 'routing' && <RoutingMatrixView products={products} />}
      </main>

      {/* Footer & Compliance Notice */}
      <footer className="border-t border-[#1B365D]/60 bg-[#040B16]/90 backdrop-blur-md py-6 text-xs text-slate-500 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>
            Customer Voice AI Platform • Independent Public Intelligence System
          </p>
          <p className="text-[11px] text-slate-500">
            Strict Separation between Observed Customer Evidence and Engineering Hypotheses.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
