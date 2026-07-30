import Image from 'next/image';
import Link from 'next/link';

interface BrandMarkProps {
  href?: string;
  compact?: boolean;
  className?: string;
}

export default function BrandMark({ href = '/', compact = false, className = '' }: BrandMarkProps) {
  const content = (
    <>
      <span className="tp-brand-glyph overflow-hidden rounded-md" aria-hidden="true">
        <Image
          src="/brand/tp-logo.jpg"
          alt="TPaper Logo"
          width={28}
          height={28}
          priority
          className="h-full w-full object-cover"
        />
      </span>
      {!compact && (
        <span className="flex min-w-0 flex-col leading-none">
          <span className="text-sm font-bold text-[var(--color-text-primary)]">TPaper</span>
          <span className="mt-1 font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-primary)]">
            TP Studio
          </span>
        </span>
      )}
    </>
  );

  if (!href) {
    return <span className={`inline-flex items-center gap-3 ${className}`}>{content}</span>;
  }

  return (
    <Link href={href} className={`inline-flex items-center gap-3 ${className}`}>
      {content}
    </Link>
  );
}
