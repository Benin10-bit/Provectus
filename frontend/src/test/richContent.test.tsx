import { expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import RichContent, { remainingAssets } from '@/components/question-bank/RichContent';
import type { Asset, ContentSegment } from '@/lib/questionBank';

it('renders a formula between text segments, preserving bold and line breaks', () => {
  const hash = 'a'.repeat(64);
  const segments: ContentSegment[] = [
    { kind: 'text', text: 'A capacitância de ', line_id: 'line1', bold: true },
    { kind: 'visual', asset_hash: hash, display: 'inline', role: 'formula', line_id: 'line1', bbox: [10, 10, 30, 20], font_size: 10 },
    { kind: 'text', text: ' é dada por', line_id: 'line1' },
    { kind: 'text', text: 'essa expressão.', line_id: 'line2' },
  ];
  const { container } = render(<RichContent segments={segments} fallback={'A capacitância de [VISUAL] é dada por'} />);
  expect(container.textContent).not.toContain('[VISUAL]');
  expect(container.querySelector('strong')?.textContent).toBe('A capacitância de ');
  const image = screen.getByRole('img', { name: 'Figura da questão' });
  expect(image).toHaveAttribute('src', `/api/api/v1/question-bank/assets/${hash}`);
  expect(container.querySelector('br')).not.toBeNull();
  expect(container.querySelector('strong')!.compareDocumentPosition(image) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  const assets: Asset[] = [
    { hash, url: `/api/v1/question-bank/assets/${hash}`, type: 'STATEMENT_IMAGE', alt: 'formula', mime_type: 'image/webp' },
    { hash: 'b'.repeat(64), url: '/other', type: 'GRAPH', alt: 'graph', mime_type: 'image/webp' },
    { hash: 'c'.repeat(64), url: '/audit', type: 'ORIGINAL_CROP', alt: 'audit', mime_type: 'image/webp' },
  ];
  expect(remainingAssets(assets, segments).map(a => a.type)).toEqual(['GRAPH']);
});
