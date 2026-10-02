import { useState, type ReactNode } from 'react';
import { assetUrl, type Asset, type ContentSegment } from '@/lib/questionBank';

const imageRoute = (hash: string) => `/api/v1/question-bank/assets/${hash}`;

export function ImageWithFallback({ url, alt, className }: { url: string; alt: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  return failed
    ? <span className="qb-image-missing" role="status">Imagem indisponível</span>
    : <img className={className} loading="lazy" src={assetUrl(url)} alt={alt} onError={() => setFailed(true)} />;
}

export function Images({ items }: { items: Asset[] }) {
  if (!items.length) return null;
  return <div className="qb-images">{items.map((asset, index) =>
    <ImageWithFallback key={`${asset.hash}-${index}`} url={asset.url} alt={asset.alt} />
  )}</div>;
}

export function remainingAssets(assets: Asset[], segments?: ContentSegment[]) {
  const inContent = new Set(segments?.filter(s => s.kind === 'visual').map(s => s.asset_hash).filter(Boolean));
  return assets.filter(asset => !inContent.has(asset.hash) && asset.type !== 'ORIGINAL_CROP');
}

export default function RichContent({ segments, fallback }: { segments?: ContentSegment[]; fallback?: string | null }) {
  if (!segments?.length) return <span className="qb-plain-content">{fallback}</span>;

  const nodes: ReactNode[] = [];
  let lastLine: string | undefined;
  segments.forEach((segment, index) => {
    if (index && segment.line_id && lastLine && segment.line_id !== lastLine) {
      nodes.push(<br key={`break-${index}`} />);
    }
    if (segment.line_id) lastLine = segment.line_id;

    if (segment.kind === 'visual') {
      const inline = segment.display === 'inline';
      const bounds = segment.bbox;
      const ratio = bounds && segment.font_size && segment.font_size > 0
        ? Math.min(2.8, Math.max(0.85, (bounds[3] - bounds[1]) / segment.font_size))
        : 1.35;
      const content = segment.asset_hash
        ? <ImageWithFallback url={imageRoute(segment.asset_hash)} alt={segment.role === 'symbol' ? 'Símbolo da questão' : 'Figura da questão'} className="qb-segment-image" />
        : <span className="qb-image-missing" role="status">Visual não disponível</span>;
      nodes.push(<span key={segment.asset_hash ?? `visual-${index}`}
        className={inline ? 'qb-visual-inline' : 'qb-visual-block'}
        style={inline ? { height: `${ratio}em` } : undefined}>{content}</span>);
      return;
    }

    let content: ReactNode = segment.text ?? '';
    if (segment.script === 'sup') content = <sup>{content}</sup>;
    if (segment.script === 'sub') content = <sub>{content}</sub>;
    if (segment.bold) content = <strong>{content}</strong>;
    nodes.push(<span key={`text-${index}`}>{content}</span>);
  });
  return <span className="qb-rich-content">{nodes}</span>;
}
