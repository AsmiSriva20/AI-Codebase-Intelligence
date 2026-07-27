import { Loader2 } from 'lucide-react';

export default function Spinner({ size = 15, color, style = {} }) {
  return (
    <Loader2
      size={size}
      color={color}
      style={{ animation: 'spin 0.8s linear infinite', flexShrink: 0, ...style }}
    />
  );
}
