type Props = {
  compact?: boolean;
  className?: string;
};

const BASE = (import.meta.env.BASE_URL || '/').replace(/\/?$/, '/');
const MARK = `${BASE}brand/skyconnect-mark.png`;
const LOGO = `${BASE}brand/skyconnect-logo.png`;

/** Official headset mark + wordmark. */
export default function SkyConnectLogo({ compact = false, className = '' }: Props) {
  if (compact) {
    return (
      <img
        src={MARK}
        alt="SkyConnect"
        className={`h-8 w-8 object-contain ${className}`}
      />
    );
  }
  return (
    <img
      src={LOGO}
      alt="SkyConnect — AI-powered omnichannel contact center"
      className={`h-9 w-auto max-w-[176px] object-contain object-left ${className}`}
    />
  );
}
