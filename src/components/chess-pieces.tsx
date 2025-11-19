import type { SVGProps } from 'react';

const pieceCommonProps: SVGProps<SVGSVGElement> = {
  viewBox: "0 0 45 45",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  className: "drop-shadow-md"
};

const pieceColorProps: Record<'w' | 'b', SVGProps<SVGSVGElement>> = {
  w: { fill: "hsl(0, 0%, 95%)", stroke: "hsl(0, 0%, 20%)" },
  b: { fill: "hsl(0, 0%, 20%)", stroke: "hsl(0, 0%, 80%)" },
};

const King = ({ color }: { color: 'w' | 'b' }) => (
  <svg {...pieceCommonProps} {...pieceColorProps[color]}>
    <path d="M22.5 11.63V6M20 8h5" fill="none" />
    <path d="M22.5 25s4.5-7.5 3-10.5c-1.5-3-7.5-3-6 0 1.5 3 3 10.5 3 10.5" />
    <path d="M12.5 37c5.5-2.5 14.5-2.5 20 0v-4.5s-1-4.5-10-4.5-10 4.5-10 4.5v4.5z" />
  </svg>
);

const Queen = ({ color }: { color: 'w' | 'b' }) => (
  <svg {...pieceCommonProps} {...pieceColorProps[color]}>
    <path d="M10 13.5s3-6 12.5-6 12.5 6 12.5 6l-2.5 11.5h-20l-2.5-11.5z" />
    <path d="M12 37.5h21v-5H12v5z" />
    <circle cx="6.5" cy="11.5" r="2.5" />
    <circle cx="14.5" cy="9.5" r="2.5" />
    <circle cx="22.5" cy="8.5" r="2.5" />
    <circle cx="30.5" cy="9.5" r="2.5" />
    <circle cx="38.5" cy="11.5" r="2.5" />
  </svg>
);

const Rook = ({ color }: { color: 'w' | 'b' }) => (
  <svg {...pieceCommonProps} {...pieceColorProps[color]}>
    <path d="M9 39h27v-3H9v3zM12 36v-4h21v4H12zM11 14V9h4v2h5V9h5v2h5V9h4v5" />
    <path d="M34 14l-3 3H14l-3-3" />
    <path d="M31 17v12.5H14V17" />
  </svg>
);

const Bishop = ({ color }: { color: 'w' | 'b' }) => (
  <svg {...pieceCommonProps} {...pieceColorProps[color]}>
    <path d="M9 36h27v-2H9v2zm18-12.5a3.5 3.5 0 01-3.5 3.5h-2a3.5 3.5 0 01-3.5-3.5V17h9v6.5z" />
    <path d="M15 34h15l-1.5-2.5h-12L15 34z" />
    <path d="M22.5 17l-3-2.5h6l-3 2.5zM22.5 8a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
  </svg>
);

const Knight = ({ color }: { color: 'w' | 'b' }) => (
  <svg {...pieceCommonProps} {...pieceColorProps[color]}>
    <path d="M22 10c10.5 1 11.5 8 11.5 10.5-1 3.5-5.5 4.5-11.5 4.5-6 0-10.5-1-11.5-4.5C9.5 18 11.5 11 22 10z" />
    <path d="M13.5 25.5s-2 2-2 4.5c0 2.5 1.5 4.5 4.5 4.5h13.5" />
    <path d="M15 29.5s-2 2-2 4.5" />
    <path d="M12 12.5s-1.5-1.5-2.5-3c-1-1.5-1-2.5-1-2.5s1 1.5 2.5 3c1.5 1.5 2.5 3 2.5 3" />
  </svg>
);

const Pawn = ({ color }: { color: 'w' | 'b' }) => (
  <svg {...pieceCommonProps} {...pieceColorProps[color]}>
    <path d="M22.5 9c-2.5 0-4.5 2-4.5 4.5s2 4.5 4.5 4.5 4.5-2 4.5-4.5-2-4.5-4.5-4.5z" />
    <path d="M12 37h21v-4H12v4zM16 33v-3h13v3H16zM18 30v-9h9v9H18z" />
  </svg>
);

const Wall = () => (
    <svg viewBox="0 0 45 45" className="p-1">
        <path d="M5 5 H 40 V 40 H 5 Z" fill="hsl(30 20% 30%)" stroke="hsl(30 20% 10%)" strokeWidth="1.5" />
        <path d="M5 16.25 H 40 M5 27.5 H 40 M16.25 5 V 16.25 M27.5 5 V 16.25 M10.625 16.25 V 27.5 M21.875 16.25 V 27.5 M33.125 16.25 V 27.5 M16.25 27.5 V 40 M27.5 27.5 V 40" 
            fill="none" stroke="hsl(30 20% 15%)" strokeWidth="1" />
    </svg>
);

const Threat = () => (
    <svg viewBox="0 0 45 45" stroke="hsl(var(--destructive))" fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="drop-shadow-md">
       <path d="M22.5 6 L22.5 12" />
       <path d="M33.4 11.6 L28.9 15.1" />
       <path d="M39 22.5 L33 22.5" />
       <path d="M33.4 33.4 L28.9 29.9" />
       <path d="M22.5 39 L22.5 33" />
       <path d="M11.6 33.4 L15.1 29.9" />
       <path d="M6 22.5 L12 22.5" />
       <path d="M11.6 11.6 L15.1 15.1" />
    </svg>
);


const PIECE_MAP: { [key: string]: (props: { color: 'w' | 'b' }) => JSX.Element } = {
  K: King, Q: Queen, R: Rook, B: Bishop, N: Knight, P: Pawn, X: Wall, T: Threat
};

export function Piece({ piece }: { piece: string | null }) {
  if (!piece) return null;
  const color = piece[0] as 'w' | 'b';
  const type = piece.length > 1 ? piece[1] : piece[0]; // Handles single char pieces like X and T
  const Component = PIECE_MAP[type];
  if (!Component) return null;

  // Wall and Threat are colorless
  if (type === 'X' || type === 'T') {
      return <div className="w-full h-full relative z-10 pointer-events-none p-1"><Component color="w" /></div>;
  }
  
  return <div className="w-full h-full relative z-10 pointer-events-none p-1"><Component color={color} /></div>;
}
