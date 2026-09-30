import React, { useState, useEffect } from 'react';
import {
  Review,
  ReviewFilterParams,
  Product,
  Source,
} from '../../types';
import { api } from '../../services/api';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { EmptyState } from '../common/EmptyState';
import { getProductMeta, SOURCE_LABELS } from '../../constants/catalog';
import {
  Search,
  PlusCircle,
  Star,
  Sparkles,
  MapPin,
  ChevronLeft,
  ChevronRight,
  Bot,
  Brain,
} from 'lucide-react';

interface ReviewExplorerViewProps {
  products: Product[];
  sources: Source[];
  onReviewIngested: () => void;
}

export const ReviewExplorerView: React.FC<ReviewExplorerViewProps> = ({
  products,
  sources,
  onReviewIngested,
}) => {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pages, setPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [selectedProduct, setSelectedProduct] = useState<string>('');
  const [selectedSource, setSelectedSource] = useState<string>('');
  const [selectedSentiment, setSelectedSentiment] = useState<string>('');
  const [selectedRating, setSelectedRating] = useState<number | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isSemanticSearch, setIsSemanticSearch] = useState<boolean>(false);

  // Modals
  const [selectedReview, setSelectedReview] = useState<Review | null>(null);
  const [isIngestModalOpen, setIsIngestModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // New review form
  const [formProduct, setFormProduct] = useState<string>('venture_x');
  const [formSource, setFormSource] = useState<string>('apple_app_store');
  const [formRating, setFormRating] = useState<number>(1);
  const [formTitle, setFormTitle] = useState<string>('');
  const [formText, setFormText] = useState<string>('');
  const [formLocation, setFormLocation] = useState<string>('');

  const loadReviews = async () => {
    setLoading(true);
    setError(null);
    try {
      if (isSemanticSearch && searchQuery.trim()) {
        const res = await api.searchSemantic(searchQuery.trim(), 20, 0.0);
        setReviews(res.results.map((r) => r.review));
        setTotal(res.total_results);
        setPages(1);
      } else {
        const params: ReviewFilterParams = {
          page,
          page_size: 25,
          product_id: selectedProduct || undefined,
          source_id: selectedSource || undefined,
          sentiment: selectedSentiment || undefined,
          rating: selectedRating,
        };
        const res = await api.getReviews(params);
        setReviews(res.items);
        setTotal(res.total);
        setPages(res.pages || 1);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch reviews');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReviews();
  }, [page, selectedProduct, selectedSource, selectedSentiment, selectedRating]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadReviews();
  };

  const handleIngestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formText.trim()) return;
    setIsSubmitting(true);
    try {
      await api.ingestReview({
        product_id: formProduct,
        source_id: formSource,
        rating: formRating,
        review_title: formTitle.trim() || undefined,
        review_text: formText.trim(),
        location: formLocation.trim() || undefined,
      });
      setIsIngestModalOpen(false);
      setFormTitle('');
      setFormText('');
      setFormLocation('');
      onReviewIngested();
      loadReviews();
    } catch (err: any) {
      alert(`Ingestion error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 3D Search & Ingest Action Toolbar */}
      <div className="bg-gradient-to-r from-[#07192F]/90 via-[#0B203B]/90 to-[#06172B]/90 border border-sky-500/30 rounded-2xl p-6 shadow-xl backdrop-blur-md relative overflow-hidden">
        <div className="absolute inset-0 cyber-grid-dense opacity-20 pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-sky-400 absolute left-3.5 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={
                  isSemanticSearch
                    ? 'Enter natural language semantic query (e.g. "lounge crowding Dallas" or "app crashing Face ID")...'
                    : 'Filter reviews by keyword text...'
                }
                className="w-full bg-[#040C18]/90 border border-[#1B365D] rounded-xl pl-10 pr-4 py-2.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400/50 transition shadow-inner"
              />
            </div>
            <button
              type="submit"
              className="px-5 py-2.5 bg-gradient-to-r from-sky-600 to-[#0076BE] hover:from-sky-500 hover:to-[#0099D8] text-white text-xs font-bold rounded-xl transition-all shadow-[0_4px_16px_rgba(56,189,248,0.3)] shrink-0 active:scale-95 border border-sky-400/40"
            >
              Search
            </button>
          </form>

          {/* Controls: Semantic toggle & Ingest review */}
          <div className="flex items-center space-x-3 shrink-0">
            <button
              type="button"
              onClick={() => {
                setIsSemanticSearch(!isSemanticSearch);
                setPage(1);
              }}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold border transition-all duration-200 active:scale-95 ${
                isSemanticSearch
                  ? 'bg-gradient-to-r from-purple-900 to-indigo-900 text-purple-200 border-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.4)]'
                  : 'bg-[#071629] text-slate-300 border-[#1B365D] hover:border-sky-500/40'
              }`}
            >
              <Sparkles className={`w-3.5 h-3.5 ${isSemanticSearch ? 'text-purple-300 animate-spin' : 'text-slate-400'}`} />
              <span>Vector Semantic Search {isSemanticSearch ? 'ON' : 'OFF'}</span>
            </button>

            <button
              type="button"
              onClick={() => setIsIngestModalOpen(true)}
              className="flex items-center space-x-1.5 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold shadow-[0_4px_16px_rgba(16,185,129,0.35)] transition-all active:scale-95 border border-emerald-400/40"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Ingest Review</span>
            </button>
          </div>
        </div>

        {/* Multi-Dimensional Filter Bar */}
        <div className="mt-4 pt-4 border-t border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
          {/* Product selector */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              Product Catalog
            </label>
            <select
              value={selectedProduct}
              onChange={(e) => {
                setSelectedProduct(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="">All 19 Products</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Source selector */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              Review Source
            </label>
            <select
              value={selectedSource}
              onChange={(e) => {
                setSelectedSource(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="">All 5 Platforms</option>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {SOURCE_LABELS[s.id]?.icon || '🌐'} {s.name}
                </option>
              ))}
            </select>
          </div>

          {/* Sentiment selector */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              AI Sentiment
            </label>
            <select
              value={selectedSentiment}
              onChange={(e) => {
                setSelectedSentiment(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="">All Sentiments</option>
              <option value="negative">Negative</option>
              <option value="neutral">Neutral</option>
              <option value="positive">Positive</option>
            </select>
          </div>

          {/* Star Rating selector */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">
              Star Rating
            </label>
            <select
              value={selectedRating !== undefined ? String(selectedRating) : ''}
              onChange={(e) => {
                setSelectedRating(e.target.value ? Number(e.target.value) : undefined);
                setPage(1);
              }}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="">All Ratings (1-5★)</option>
              <option value="1">1 Star</option>
              <option value="2">2 Stars</option>
              <option value="3">3 Stars</option>
              <option value="4">4 Stars</option>
              <option value="5">5 Stars</option>
            </select>
          </div>

          {/* Clear Filters button */}
          <div className="flex items-end">
            <button
              type="button"
              onClick={() => {
                setSelectedProduct('');
                setSelectedSource('');
                setSelectedSentiment('');
                setSelectedRating(undefined);
                setSearchQuery('');
                setIsSemanticSearch(false);
                setPage(1);
              }}
              className="w-full py-1.5 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg border border-slate-700 transition"
            >
              Reset Filters
            </button>
          </div>
        </div>
      </div>

      {/* Review List Content */}
      <div className="bg-[#071629]/90 border border-sky-500/30 rounded-2xl overflow-hidden shadow-2xl backdrop-blur-md">
        <div className="px-6 py-4 border-b border-[#1B365D] flex items-center justify-between bg-[#051121]/60">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-bold text-white tracking-tight">
              {total.toLocaleString()} Reviews Found
            </span>
            {isSemanticSearch && (
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-700 shadow-sm font-mono">
                Sorted by pgvector cosine similarity
              </span>
            )}
          </div>
          <span className="text-xs text-slate-400 font-mono">
            Page {page} of {pages}
          </span>
        </div>

        {loading ? (
          <LoadingSpinner message="Searching customer feedback..." />
        ) : error ? (
          <div className="p-8 text-center text-rose-400 text-sm">{error}</div>
        ) : reviews.length === 0 ? (
          <EmptyState
            title="No reviews match your filters"
            description="Try loosening your product, sentiment, or search keyword filters."
            actionLabel="Reset Filters"
            onAction={() => {
              setSelectedProduct('');
              setSelectedSource('');
              setSelectedSentiment('');
              setSelectedRating(undefined);
              setSearchQuery('');
              setIsSemanticSearch(false);
              setPage(1);
            }}
          />
        ) : (
          <div className="divide-y divide-[#1B365D]/60">
            {reviews.map((review) => {
              const meta = getProductMeta(review.product_id);
              const sourceMeta = SOURCE_LABELS[review.source_id] || {
                name: review.source_id,
                icon: '📡',
              };
              const analysis = review.analysis;

              return (
                <div
                  key={review.id}
                  onClick={() => setSelectedReview(review)}
                  className="p-5 hover:bg-[#0E2849] transition-all duration-150 cursor-pointer group bg-[#071629]/60 border-b border-[#1B365D]/60 hover:border-sky-500/40"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    {/* Capital One Product Card Pill and Source */}
                    <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                      <span
                        className={`text-xs px-2.5 py-1 rounded-md border font-bold flex items-center space-x-1.5 shadow-sm ${meta.cardStyle}`}
                      >
                        <span>💳</span>
                        <span>{meta.name}</span>
                        <span className="text-[10px] opacity-75 font-normal hidden sm:inline">({meta.tier})</span>
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-[#071527] text-slate-300 border border-[#1B365D]">
                        {sourceMeta.icon} {sourceMeta.name}
                      </span>
                      {review.location && (
                        <span className="flex items-center text-xs text-slate-400">
                          <MapPin className="w-3 h-3 mr-1 text-[#D03027]" />
                          {review.location}
                        </span>
                      )}
                    </div>

                    {/* Rating stars & Timestamp */}
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center text-[#FBBF24]">
                        {[...Array(5)].map((_, i) => (
                          <Star
                            key={i}
                            className={`w-3.5 h-3.5 ${
                              i < review.rating ? 'fill-current text-[#FBBF24]' : 'text-slate-700'
                            }`}
                          />
                        ))}
                      </div>
                      <span className="text-xs text-slate-500 font-mono">
                        {review.created_at ? review.created_at.slice(0, 10) : ''}
                      </span>
                    </div>
                  </div>

                  {/* Review Text */}
                  {review.review_title && (
                    <h4 className="text-sm font-bold text-slate-100 mb-1 group-hover:text-[#38BDF8] transition">
                      {review.review_title}
                    </h4>
                  )}
                  <p className="text-xs text-slate-300 leading-relaxed line-clamp-2">
                    "{review.review_text}"
                  </p>

                  {/* AI Structured Extraction Tags */}
                  {analysis && (
                    <div className="mt-3 flex items-center space-x-2 flex-wrap gap-y-1 pt-2 border-t border-[#1B365D]/60">
                      <div className="flex items-center text-[11px] text-slate-400 mr-2">
                        <Bot className="w-3.5 h-3.5 mr-1 text-[#38BDF8]" />
                        <span className="font-semibold text-slate-300">AI Extraction:</span>
                      </div>
                      <Badge variant="sentiment" value={analysis.sentiment}>
                        {analysis.sentiment} ({analysis.sentiment_score > 0 ? `+${analysis.sentiment_score}` : analysis.sentiment_score})
                      </Badge>
                      <Badge variant="severity" value={analysis.severity}>
                        {analysis.severity}
                      </Badge>
                      <span className="text-[11px] px-2 py-0.5 rounded bg-[#071527] text-slate-300 border border-[#1B365D] font-mono">
                        {analysis.category}
                      </span>
                      <span className="text-[11px] text-slate-400 italic truncate max-w-xs">
                        → {analysis.issue}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination bar */}
        {pages > 1 && (
          <div className="px-6 py-4 border-t border-slate-800 flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40 transition"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>
            <span className="text-xs text-slate-400">
              Page {page} of {pages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(pages, p + 1))}
              disabled={page >= pages}
              className="flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40 transition"
            >
              <span>Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Review Detail Inspection Modal */}
      {selectedReview && (
        <Modal
          isOpen={!!selectedReview}
          onClose={() => setSelectedReview(null)}
          title={selectedReview.review_title || 'Customer Review Details'}
          subtitle={`Review ID: ${selectedReview.id}`}
        >
          <div className="space-y-4">
            {/* Metadata bar */}
            <div className="flex items-center space-x-3 flex-wrap gap-y-1">
              <Badge variant="default" className="text-xs font-medium">
                {getProductMeta(selectedReview.product_id).name}
              </Badge>
              <span className="text-xs text-slate-400">
                Source: {SOURCE_LABELS[selectedReview.source_id]?.name || selectedReview.source_id}
              </span>
              <div className="flex items-center text-amber-400 text-xs">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={`w-3.5 h-3.5 ${
                      i < selectedReview.rating ? 'fill-current text-amber-400' : 'text-slate-600'
                    }`}
                  />
                ))}
              </div>
              {selectedReview.location && (
                <span className="text-xs text-slate-400 flex items-center">
                  <MapPin className="w-3 h-3 mr-1" />
                  {selectedReview.location}
                </span>
              )}
            </div>

            {/* Verbatim quote */}
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                Verbatim Customer Feedback
              </span>
              <p className="text-sm text-slate-200 leading-relaxed italic">
                "{selectedReview.review_text}"
              </p>
            </div>

            {/* AI Analysis Structured Details */}
            {selectedReview.analysis ? (
              <div className="p-4 rounded-xl bg-sky-950/20 border border-sky-800/40 space-y-3">
                <div className="flex items-center space-x-2">
                  <Brain className="w-4 h-4 text-sky-400" />
                  <span className="text-xs font-semibold text-sky-300 uppercase tracking-wider">
                    AI Structured Extraction Result
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                  <div>
                    <span className="text-slate-400 block">Category</span>
                    <span className="text-slate-200 font-medium">
                      {selectedReview.analysis.category}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Identified Issue</span>
                    <span className="text-slate-200 font-medium">
                      {selectedReview.analysis.issue}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Severity Level</span>
                    <Badge variant="severity" value={selectedReview.analysis.severity}>
                      {selectedReview.analysis.severity}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Sentiment Score</span>
                    <Badge variant="sentiment" value={selectedReview.analysis.sentiment}>
                      {selectedReview.analysis.sentiment} ({selectedReview.analysis.sentiment_score})
                    </Badge>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Extraction Confidence</span>
                    <span className="text-emerald-400 font-mono font-medium">
                      {Math.round(selectedReview.analysis.confidence * 100)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Customer Intent</span>
                    <span className="text-slate-300">
                      {selectedReview.analysis.customer_intent || 'General Feedback'}
                    </span>
                  </div>
                </div>

                {selectedReview.analysis.entities && selectedReview.analysis.entities.length > 0 && (
                  <div className="pt-2 border-t border-sky-900/40">
                    <span className="text-xs text-slate-400 block mb-1">
                      Named Entities / Attributes:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedReview.analysis.entities.map((e, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 font-mono border border-slate-700"
                        >
                          {JSON.stringify(e)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-3 bg-slate-800/40 rounded-lg text-xs text-slate-400">
                AI extraction in progress or awaiting worker consumer.
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Ingest Review Modal */}
      {isIngestModalOpen && (
        <Modal
          isOpen={isIngestModalOpen}
          onClose={() => setIsIngestModalOpen(false)}
          title="Ingest Customer Review"
          subtitle="Submit live feedback to trigger Kafka publishing, AI analysis, vector embeddings, and cluster discovery."
        >
          <form onSubmit={handleIngestSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Product *
                </label>
                <select
                  value={formProduct}
                  onChange={(e) => setFormProduct(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200"
                  required
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.family})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Platform / Source *
                </label>
                <select
                  value={formSource}
                  onChange={(e) => setFormSource(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200"
                  required
                >
                  {sources.map((s) => (
                    <option key={s.id} value={s.id}>
                      {SOURCE_LABELS[s.id]?.icon || '🌐'} {s.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Star Rating (1 to 5) *
                </label>
                <select
                  value={formRating}
                  onChange={(e) => setFormRating(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200"
                >
                  <option value={1}>1 Star - Critical Dissatisfaction</option>
                  <option value={2}>2 Stars - Poor Experience</option>
                  <option value={3}>3 Stars - Neutral / Mixed</option>
                  <option value={4}>4 Stars - Good Experience</option>
                  <option value={5}>5 Stars - Excellent Experience</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Location (Optional)
                </label>
                <input
                  type="text"
                  value={formLocation}
                  onChange={(e) => setFormLocation(e.target.value)}
                  placeholder="e.g. Austin Downtown Café, DFW Terminal D"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Review Title (Optional)
              </label>
              <input
                type="text"
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                placeholder="e.g. Lounge entry denied despite Venture X card"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Review Text *
              </label>
              <textarea
                value={formText}
                onChange={(e) => setFormText(e.target.value)}
                placeholder="Enter customer feedback text..."
                rows={4}
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 leading-relaxed"
              />
            </div>

            <div className="flex justify-end space-x-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsIngestModalOpen(false)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-slate-200 bg-slate-800 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-2 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition disabled:opacity-50"
              >
                {isSubmitting ? 'Ingesting...' : 'Submit & Analyze'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
