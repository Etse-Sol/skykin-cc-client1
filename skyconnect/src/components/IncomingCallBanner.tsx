import { useLocation, useNavigate } from 'react-router-dom';
import { useSoftphone } from '../softphone/SoftphoneContext';

/**
 * Ring / outbound controls on every agent page EXCEPT Live call —
 * Live call already has its own Answer / Cancel bar (avoid duplicate).
 */
export default function IncomingCallBanner() {
  const phone = useSoftphone();
  const navigate = useNavigate();
  const loc = useLocation();

  // Live call page has its own ringing/calling UI
  if (loc.pathname === '/agent/calls' || loc.pathname === '/agent/interaction') {
    return null;
  }

  if (phone.phase !== 'ringing' && phone.phase !== 'calling') {
    return null;
  }

  const goLive = () => {
    navigate('/agent/interaction');
  };

  if (phone.phase === 'ringing') {
    return (
      <div
        className="sticky top-0 z-[40] flex flex-wrap items-center justify-center gap-3 border-b border-[var(--color-sc-green)] bg-[#E2F0D9] px-4 py-3 shadow-sm"
        role="alertdialog"
        aria-label="Incoming call"
      >
        <span className="animate-pulse sc-section-title">
          Incoming call — {phone.remoteNumber || 'Unknown'}
        </span>
        <button
          type="button"
          onClick={() => {
            void phone.answer();
            goLive();
          }}
          className="rounded-lg bg-[var(--color-sc-green)] px-5 py-2 text-sm font-semibold text-white"
        >
          Answer
        </button>
        <button
          type="button"
          onClick={phone.decline}
          className="rounded-lg bg-[#D9534F] px-5 py-2 text-sm font-semibold text-white"
        >
          Decline
        </button>
        <button
          type="button"
          onClick={goLive}
          className="rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-xs font-bold text-[var(--color-sc-forest)]"
        >
          Open Live call
        </button>
      </div>
    );
  }

  return (
    <div
      className="sticky top-0 z-[40] flex flex-wrap items-center justify-center gap-3 border-b border-[#2D8CFF] bg-[#E8F2FF] px-4 py-3 shadow-sm"
      role="status"
      aria-label="Outbound call"
    >
      <span className="text-sm font-bold text-[#1a6fd4]">
        Calling — {phone.remoteNumber || '…'}
      </span>
      <button
        type="button"
        onClick={phone.hangup}
        className="rounded-lg bg-[#D9534F] px-5 py-2 text-sm font-semibold text-white"
      >
        Cancel
      </button>
      <button
        type="button"
        onClick={goLive}
        className="rounded-lg border border-[var(--color-sc-line)] bg-white px-3 py-2 text-xs font-bold text-[#1a6fd4]"
      >
        Open Live call
      </button>
    </div>
  );
}
