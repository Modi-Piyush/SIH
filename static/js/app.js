/**
 * e-Kisan Krishi Samridhi - Main Application Controller
 * SIH Problem Statement: PS 26032
 */

// Application State
const state = {
  currentLang: 'en',
  currentRole: 'view-farmer',
  selectedCrop: 'Wheat',
  selectedCenterId: 1,
  crops: [
    { name: 'Wheat', category: 'Grains', multiplier: 18, msp: 2275, icon: '🌾' },
    { name: 'Paddy', category: 'Grains', multiplier: 20, msp: 2300, icon: '🌾' },
    { name: 'Maize', category: 'Grains', multiplier: 16, msp: 2090, icon: '🌽' },
    { name: 'Bajra', category: 'Grains', multiplier: 12, msp: 2500, icon: '🌾' },
    { name: 'Jowar', category: 'Grains', multiplier: 10, msp: 3180, icon: '🌾' },
    { name: 'Tur', category: 'Pulses', multiplier: 8, msp: 7550, icon: '🫘' },
    { name: 'Chana', category: 'Pulses', multiplier: 8, msp: 5440, icon: '🫘' },
    { name: 'Masoor', category: 'Pulses', multiplier: 7, msp: 6425, icon: '🫘' },
    { name: 'Moong', category: 'Pulses', multiplier: 6.5, msp: 8558, icon: '🫘' },
    { name: 'Urad', category: 'Pulses', multiplier: 6.5, msp: 6950, icon: '🫘' }
  ],
  centers: [],
  activeTokenData: null,
  ivrSession: {
    sessionId: `IVR-${Date.now()}`,
    step: 1,
    phone: '9876543210',
    name: 'रामेश कुमार',
    crop: 'Wheat',
    acres: 3.5,
    centerId: 1,
    promptHindi: 'नमस्ते! सरकारी ई-खरीद किसान सेवा में आपका स्वागत है। कृपया अपनी फसल चुनने के लिए 1 दबाएं या बोलें।'
  }
};

// Bilingual Translations (Hindi & English)
const i18n = {
  en: {
    app_title: 'e-Kisan Krishi Samridhi',
    app_subtitle: 'Smart Storage-Aware Procurement & AI Quality Supply Chain Platform',
    nav_farmer: 'Farmer Portal',
    nav_guard: 'Gatekeeper (Offline)',
    nav_clerk: 'Mandi Quality & Weigh',
    nav_admin: 'Admin Command',
    nav_voice: 'Hindi Voice IVR',
    farmer_tab_book: 'Smart Slot Booking',
    farmer_tab_track: 'Track My Token',
    farmer_tab_prescreen: 'AI Moisture Pre-Check',
    farmer_tab_history: 'History & SMS Inbox',
    booking_title: 'Smart Storage-Aware Slot Booking',
    booking_subtitle: 'Guaranteed 2-hour arrival slot, auto-tranching for large loads, and smallholder equity protection.',
    lbl_phone: 'Mobile Number (10 Digits)',
    lbl_name: 'Farmer Full Name',
    lbl_village: 'Village / Gram',
    lbl_land: 'Landholding Area (Acres)',
    lbl_crop: 'Select Crop to Procure',
    lbl_yield_estimate: 'Yield Estimation & Capping',
    lbl_select_center: 'Select Procurement Center (PACS Godown)',
    lbl_tractor: 'Tractor / Vehicle Number',
    lbl_weight_mode: 'Quantity Input Method',
    opt_mode_land: 'Landholding Area (Acres)',
    opt_mode_exact: 'Exact Crop Weight (Quintals)',
    lbl_exact_weight: 'Exact Crop Weight (Quintals)',
    btn_confirm_booking: 'Confirm Booking & Generate Digital Token',
    track_title: 'Live Digital Token Tracker',
    track_subtitle: 'Real-time gate check-in, AI quality status, weighbridge report, and instant payment dispatch.',
    prescreen_title: 'AI Crop Quality & Moisture Pre-Check',
    history_title: 'My Procurement History & SMS Alerts'
  },
  hi: {
    app_title: 'ई-किसान कृषि समृद्धि',
    app_subtitle: 'स्मार्ट गोदाम क्षमता आधारित ई-खरीद, एआई गुणवत्ता व ऑफलाइन सप्लाई चेन प्लेटफॉर्म',
    nav_farmer: 'किसान पोर्टल',
    nav_guard: 'गेटकीपर (ऑफलाइन)',
    nav_clerk: 'मंडी गुणवत्ता व धर्मकांटा',
    nav_admin: 'जिला नियंत्रण कक्ष',
    nav_voice: 'हिंदी वॉइस आईवीआर',
    farmer_tab_book: 'स्मार्ट स्लॉट बुकिंग',
    farmer_tab_track: 'टोकन लाइव स्थिति',
    farmer_tab_prescreen: 'एआई नमी पूर्व-जांच',
    farmer_tab_history: 'इतिहास व एसएमएस',
    booking_title: 'स्मार्ट भंडारण-आधारित स्लॉट बुकिंग',
    booking_subtitle: 'निश्चित 2 घंटे का आगमन स्लॉट, बड़े किसानों के लिए चरणबद्ध बुकिंग, एवं छोटे किसानों का 40% कोटा आरक्षण।',
    lbl_phone: 'मोबाइल नंबर (10 अंक)',
    lbl_name: 'किसान का पूरा नाम',
    lbl_village: 'गांव / ग्राम',
    lbl_land: 'जमीन का रकबा (एकड़)',
    lbl_crop: 'क्रय हेतु फसल चुनें',
    lbl_yield_estimate: 'उपज अनुमान एवं कोटा सीमा',
    lbl_select_center: 'क्रय केंद्र (पैक्स गोदाम) चुनें',
    lbl_tractor: 'ट्रैक्टर / वाहन संख्या',
    lbl_weight_mode: 'मात्रा प्रविष्टि विधि',
    opt_mode_land: 'जमीन का रकबा (एकड़)',
    opt_mode_exact: 'सटीक फसल वजन (क्विंटल)',
    lbl_exact_weight: 'सटीक फसल वजन (क्विंटल)',
    btn_confirm_booking: 'बुकिंग की पुष्टि करें व डिजिटल टोकन प्राप्त करें',
    track_title: 'डिजिटल टोकन लाइव ट्रैकर',
    track_subtitle: 'गेट चेक-इन, एआई गुणवत्ता परीक्षण, धर्मकांटा रिपोर्ट एवं प्रत्यक्ष बैंक हस्तांतरण (DBT)।',
    prescreen_title: 'एआई फसल गुणवत्ता व नमी पूर्व-परीक्षण',
    history_title: 'खरीद इतिहास एवं मोबाइल एसएमएस संदेश'
  }
};

// UI Notification Helper
function showToast(title, message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div>
      <div style="font-weight: 700; font-size: 0.9rem;">${title}</div>
      <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.2rem;">${message}</div>
    </div>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

// Language Switcher
function setLanguage(lang) {
  state.currentLang = lang;
  document.getElementById('current-lang-text').innerText = lang === 'en' ? 'हिन्दी' : 'English';

  const dict = i18n[lang];
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (dict[key]) {
      el.innerText = dict[key];
    }
  });

  document.getElementById('app-title').innerText = dict.app_title;
  document.getElementById('app-subtitle').innerText = dict.app_subtitle;
}

// Tab Navigation
function setupNavigation() {
  // Main Role Tabs
  document.querySelectorAll('.nav-tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      state.currentRole = targetId;

      document.querySelectorAll('.nav-tab').forEach((b) => {
        b.classList.remove('btn-primary');
        b.classList.add('btn-secondary');
      });
      btn.classList.remove('btn-secondary');
      btn.classList.add('btn-primary');

      document.querySelectorAll('.view-section').forEach((sec) => {
        sec.style.display = 'none';
      });
      document.getElementById(targetId).style.display = 'block';

      // Trigger role-specific refresh
      if (targetId === 'view-admin') loadAdminDashboard();
      if (targetId === 'view-clerk') loadClerkQueue();
      if (targetId === 'view-guard') refreshGuardManifest();
    });
  });

  // Farmer Subtabs
  document.querySelectorAll('.farmer-subtab').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-subtarget');

      document.querySelectorAll('.farmer-subtab').forEach((b) => {
        b.classList.remove('btn-primary');
        b.classList.add('btn-secondary');
      });
      btn.classList.remove('btn-secondary');
      btn.classList.add('btn-primary');

      document.querySelectorAll('.farmer-subview').forEach((sub) => {
        sub.style.display = 'none';
      });
      document.getElementById(targetId).style.display = 'block';

      if (targetId === 'farmer-history') loadFarmerHistory();
    });
  });

  // Language Toggle
  document.getElementById('lang-toggle-btn').addEventListener('click', () => {
    setLanguage(state.currentLang === 'en' ? 'hi' : 'en');
  });

  // Offline Simulator Toggle for Judges
  const simToggle = document.getElementById('offline-sim-toggle');
  simToggle.addEventListener('change', (e) => {
    window.offlineStorage.setSimulatedOffline(e.target.checked);
  });

  window.offlineStorage.onNetworkChange((isOnline) => {
    const badge = document.getElementById('network-status-badge');
    const guardBadge = document.getElementById('guard-status-badge');
    const guardBanner = document.getElementById('guard-offline-banner');

    if (isOnline) {
      badge.className = 'badge badge-safe';
      badge.innerText = 'Online';
      if (guardBadge) {
        guardBadge.className = 'badge badge-safe';
        guardBadge.innerText = 'GATE NODE: ONLINE';
      }
      if (guardBanner) {
        guardBanner.style.background = 'rgba(16, 185, 129, 0.15)';
        guardBanner.style.borderColor = 'rgba(16, 185, 129, 0.3)';
      }
      showToast('Network Restored', 'Back online. Automatic sync triggered.', 'safe');
    } else {
      badge.className = 'badge badge-warning badge-pulse';
      badge.innerText = 'OFFLINE (Sync Mode)';
      if (guardBadge) {
        guardBadge.className = 'badge badge-warning badge-pulse';
        guardBadge.innerText = 'GATE NODE: OFFLINE (LOCAL DB)';
      }
      if (guardBanner) {
        guardBanner.style.background = 'rgba(245, 158, 11, 0.15)';
        guardBanner.style.borderColor = 'rgba(245, 158, 11, 0.4)';
      }
      showToast('Offline Mode Active', 'Operating via IndexedDB. Transactions will queue locally.', 'warning');
    }
    updateGuardSyncCount();
  });
}

// -----------------------------------------------------------------------------
// 1. FARMER PORTAL LOGIC
// -----------------------------------------------------------------------------
function renderCropSelector() {
  const container = document.getElementById('crop-selector-grid');
  if (!container) return;

  container.innerHTML = '';
  state.crops.forEach((c) => {
    const isSelected = c.name === state.selectedCrop;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `btn btn-sm ${isSelected ? 'btn-primary' : 'btn-secondary'}`;
    btn.style.flexDirection = 'column';
    btn.style.padding = '0.65rem 0.5rem';
    btn.style.gap = '0.2rem';
    btn.innerHTML = `
      <span style="font-size: 1.2rem;">${c.icon}</span>
      <span style="font-weight: 700; font-size: 0.85rem;">${c.name}</span>
      <span style="font-size: 0.65rem; color: ${isSelected ? '#d1fae5' : 'var(--text-muted)'};">${c.multiplier} Q/Acre</span>
    `;

    btn.addEventListener('click', () => {
      state.selectedCrop = c.name;
      renderCropSelector();
      updateYieldCalculation();
    });

    container.appendChild(btn);
  });
}

async function updateYieldCalculation() {
  const weightMode = document.getElementById('book-weight-mode')?.value || 'ESTIMATE';
  const landInput = document.getElementById('book-land');
  const exactWeightInput = document.getElementById('book-exact-weight');
  const cropObj = state.crops.find((c) => c.name === state.selectedCrop);
  const multiplier = cropObj ? cropObj.multiplier : 18;

  let acres = 3.5;
  let exactWeight = 0;

  if (weightMode === 'EXACT') {
    exactWeight = parseFloat(exactWeightInput?.value) || 50.0;
    acres = exactWeight > 0 ? (exactWeight / multiplier) : 3.5;
  } else {
    acres = parseFloat(landInput?.value) || 3.5;
    exactWeight = acres * multiplier;
  }

  const isSmall = acres <= 5.0;

  // Update Equity badge
  const eqBadge = document.getElementById('farmer-equity-badge');
  if (eqBadge) {
    if (isSmall) {
      eqBadge.className = 'badge badge-safe';
      eqBadge.innerText = weightMode === 'EXACT'
        ? `Small Farmer (≤50 Q / ~${acres.toFixed(1)} Ac) - Guaranteed 40% Center Quota`
        : `Small Farmer (${acres.toFixed(1)} Ac ≤ 5 Ac) - Guaranteed 40% Center Quota`;
    } else {
      eqBadge.className = 'badge badge-warning';
      eqBadge.innerText = weightMode === 'EXACT'
        ? `Large Farmer (>50 Q / ~${acres.toFixed(1)} Ac) - 50Q Daily Capping Applied`
        : `Large Farmer (${acres.toFixed(1)} Ac > 5 Ac) - 50Q Daily Capping Applied`;
    }
  }

  const reqBody = {
    crop_name: state.selectedCrop,
    land_acres: acres,
    mode: weightMode
  };

  if (weightMode === 'EXACT' && exactWeight > 0) {
    reqBody.exact_weight_q = exactWeight;
  }

  try {
    const res = await fetch('/api/farmer/calculate-weight', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody)
    });
    const data = await res.json();

    const previewSubtitle = weightMode === 'EXACT'
      ? `Exact Specified`
      : `@ ${data.multiplier_q_per_acre} Q/Acre`;

    document.getElementById('yield-preview-text').innerText = `${data.total_weight_q} Quintals (${data.crop_name} ${previewSubtitle})`;
    document.getElementById('yield-msp-text').innerText = `Estimated Gross MSP Value: ₹${data.estimated_gross_payout.toLocaleString('en-IN')} (Rate: ₹${data.msp_rate_per_q}/Q)`;

    const timeline = document.getElementById('tranche-timeline-container');
    const trancheBadge = document.getElementById('tranche-badge');

    if (data.requires_tranching) {
      trancheBadge.className = 'badge badge-warning badge-pulse';
      trancheBadge.innerText = `Auto-Split into ${data.tranches.length} Tranches (50Q Cap)`;
      timeline.style.display = 'block';

      let timelineHtml = `<div style="font-size: 0.8rem; font-weight: 700; color: var(--warning); margin-bottom: 0.5rem;">📅 Auto-Tranching Schedule (Social Equity 50Q Daily Limit):</div><div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">`;
      data.tranches.forEach((t) => {
        timelineHtml += `
          <div class="glass-card" style="padding: 0.5rem 0.75rem; font-size: 0.75rem; border-color: var(--warning);">
            <strong>Tranche ${t.tranche_number}/${t.total_tranches}:</strong> ${t.allocated_weight_q} Q<br>
            <span style="color: var(--text-muted);">Date: ${t.scheduled_date}</span>
          </div>
        `;
      });
      timelineHtml += '</div>';
      timeline.innerHTML = timelineHtml;
    } else {
      trancheBadge.className = 'badge badge-safe';
      trancheBadge.innerText = 'Single 1-Day Booking (≤50 Q)';
      timeline.style.display = 'none';
    }
  } catch (err) {
    console.error('Yield calc error:', err);
  }
}

async function loadProcurementCenters() {
  try {
    const res = await fetch('/api/farmer/centers');
    const centers = await res.json();
    state.centers = centers;

    const container = document.getElementById('center-selection-grid');
    if (!container) return;

    container.innerHTML = '';
    centers.forEach((c) => {
      const isSelected = c.id === state.selectedCenterId;
      const isLocked = c.storage_state === 'Critical';

      let badgeClass = 'badge-safe';
      let stateColor = '#34d399';
      if (c.storage_state === 'Warning') {
        badgeClass = 'badge-warning';
        stateColor = '#fbbf24';
      } else if (c.storage_state === 'Critical') {
        badgeClass = 'badge-critical';
        stateColor = '#f87171';
      }

      const card = document.createElement('div');
      card.className = `glass-card ${isSelected ? 'selected-center' : ''}`;
      if (isSelected) {
        card.style.borderColor = 'var(--primary)';
        card.style.background = 'rgba(16, 185, 129, 0.1)';
      }
      if (isLocked) {
        card.style.borderColor = 'rgba(239, 68, 68, 0.4)';
      }

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
          <div>
            <h4 style="font-size: 0.95rem; color: #ffffff; font-weight: 700;">${c.name}</h4>
            <span style="font-size: 0.75rem; color: var(--text-muted);">${c.code} • ${c.district}</span>
          </div>
          <span class="badge ${badgeClass}">${c.storage_state} (${c.s_fill_percentage}%)</span>
        </div>

        <div class="storage-bar-container" style="margin: 0.5rem 0;">
          <div class="storage-bar-fill storage-${c.storage_state.toLowerCase()}" style="width: ${Math.min(100, c.s_fill_percentage)}%;"></div>
        </div>

        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.75rem;">
          <span>Stock: ${c.current_stock_q} Q</span>
          <span>Incoming: ${c.incoming_booked_q} Q</span>
          <span>Max: ${c.max_capacity_q} Q</span>
        </div>

        ${isLocked && c.reroute_recommendation ? `
          <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: var(--radius-sm); padding: 0.5rem; font-size: 0.75rem; margin-bottom: 0.75rem; color: #fca5a5;">
            <strong>⛔ Center Full (≥95% Lock):</strong><br>
            Recommended Nearest Alternative: <strong>${c.reroute_recommendation.name}</strong> (${c.reroute_recommendation.distance_km} km away, ${c.reroute_recommendation.s_fill}% storage).
            <button type="button" class="btn btn-secondary btn-sm" style="margin-top: 0.4rem; width: 100%; font-size: 0.7rem; padding: 0.25rem 0.5rem;" onclick="selectReroutedCenter(${c.reroute_recommendation.id})">
              👉 Switch to ${c.reroute_recommendation.name}
            </button>
          </div>
        ` : ''}

        <button type="button" class="btn btn-sm ${isSelected ? 'btn-primary' : 'btn-secondary'}" style="width: 100%; font-size: 0.8rem;" ${isLocked ? 'disabled' : ''} onclick="selectCenter(${c.id})">
          ${isLocked ? '🔒 Bookings Locked (Full)' : isSelected ? '✓ Selected Center' : 'Select This Center'}
        </button>
      `;

      container.appendChild(card);
    });
  } catch (err) {
    console.error('Load centers error:', err);
  }
}

function selectCenter(centerId) {
  state.selectedCenterId = centerId;
  loadProcurementCenters();
}

function selectReroutedCenter(centerId) {
  state.selectedCenterId = centerId;
  loadProcurementCenters();
  showToast('Rerouting Applied', 'Switched to nearest PACS depot with available capacity.', 'safe');
}

// Slot Booking Form Submission
function setupBookingForm() {
  const form = document.getElementById('slot-booking-form');
  if (!form) return;

  const landInput = document.getElementById('book-land');
  const weightModeSelect = document.getElementById('book-weight-mode');
  const exactWeightInput = document.getElementById('book-exact-weight');
  const landInputGroup = document.getElementById('land-input-group');
  const exactWeightGroup = document.getElementById('exact-weight-group');

  function handleWeightModeChange() {
    const isExact = weightModeSelect && weightModeSelect.value === 'EXACT';
    if (isExact) {
      if (landInputGroup) landInputGroup.style.display = 'none';
      if (exactWeightGroup) exactWeightGroup.style.display = 'block';
      if (landInput) landInput.removeAttribute('required');
      if (exactWeightInput) exactWeightInput.setAttribute('required', 'required');
      if (exactWeightInput && (!exactWeightInput.value || parseFloat(exactWeightInput.value) <= 0)) {
        const cropObj = state.crops.find((c) => c.name === state.selectedCrop);
        const multiplier = cropObj ? cropObj.multiplier : 18;
        const acres = parseFloat(landInput?.value) || 3.5;
        exactWeightInput.value = (acres * multiplier).toFixed(1);
      }
    } else {
      if (landInputGroup) landInputGroup.style.display = 'block';
      if (exactWeightGroup) exactWeightGroup.style.display = 'none';
      if (landInput) landInput.setAttribute('required', 'required');
      if (exactWeightInput) exactWeightInput.removeAttribute('required');
    }
    updateYieldCalculation();
  }

  if (landInput) {
    landInput.addEventListener('input', updateYieldCalculation);
  }

  if (weightModeSelect) {
    weightModeSelect.addEventListener('change', handleWeightModeChange);
  }

  if (exactWeightInput) {
    exactWeightInput.addEventListener('input', updateYieldCalculation);
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const phone = document.getElementById('book-phone').value.trim();
    const name = document.getElementById('book-name').value.trim();
    const village = document.getElementById('book-village').value.trim();
    const tractor = document.getElementById('book-tractor').value.trim();
    const weightMode = document.getElementById('book-weight-mode').value;
    const cropObj = state.crops.find((c) => c.name === state.selectedCrop);
    const multiplier = cropObj ? cropObj.multiplier : 18;

    let land = 3.5;
    let exactWeight = null;

    if (weightMode === 'EXACT') {
      exactWeight = parseFloat(document.getElementById('book-exact-weight')?.value) || 50.0;
      land = parseFloat((exactWeight / multiplier).toFixed(2));
    } else {
      land = parseFloat(document.getElementById('book-land').value) || 3.5;
    }

    const btn = document.getElementById('btn-submit-booking');
    btn.disabled = true;
    btn.innerText = '⏳ Processing Booking & Equity Quotas...';

    try {
      // 1. Auto Register/Login farmer
      await fetch('/api/farmer/register-or-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, name, village, land_acres: land })
      });

      const bookingPayload = {
        phone,
        center_id: state.selectedCenterId,
        crop_name: state.selectedCrop,
        land_acres: land,
        tractor_number: tractor,
        weight_input_mode: weightMode
      };

      if (weightMode === 'EXACT' && exactWeight && exactWeight > 0) {
        bookingPayload.requested_weight_q = exactWeight;
      }

      // 2. Book Slot
      const res = await fetch('/api/farmer/book-slot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bookingPayload)
      });

      const data = await res.json();

      if (!res.ok) {
        if (res.status === 423) {
          // Locked
          showToast('Center Storage Critical', data.detail.message, 'danger');
        } else {
          showToast('Booking Notice', data.detail ? data.detail.message || data.detail : 'Booking could not be completed.', 'warning');
        }
        btn.disabled = false;
        btn.innerHTML = '🎟️ <span data-i18n="btn_confirm_booking">Confirm Booking & Generate Digital Token</span>';
        return;
      }

      showToast('Booking Confirmed!', `Token ${data.primary_token} issued. Arrival window: ${data.queue_info.window}`, 'safe');

      // Auto switch to Token Tracking view
      document.getElementById('track-token-input').value = data.primary_token;
      fetchAndDisplayToken(data.primary_token);

      // Switch subtab
      document.querySelectorAll('.farmer-subtab').forEach((b) => {
        b.classList.remove('btn-primary');
        b.classList.add('btn-secondary');
      });
      const trackSubtab = document.querySelector('[data-subtarget="farmer-track"]');
      if (trackSubtab) {
        trackSubtab.classList.remove('btn-secondary');
        trackSubtab.classList.add('btn-primary');
      }
      document.querySelectorAll('.farmer-subview').forEach((s) => s.style.display = 'none');
      document.getElementById('farmer-track').style.display = 'block';

      // Refresh center list to show updated incoming capacity
      loadProcurementCenters();

    } catch (err) {
      console.error('Booking submission error:', err);
      showToast('Error', 'Failed to connect to booking engine.', 'danger');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '🎟️ <span data-i18n="btn_confirm_booking">Confirm Booking & Generate Digital Token</span>';
    }
  });

  // Track Token Search button
  document.getElementById('btn-search-token').addEventListener('click', () => {
    const code = document.getElementById('track-token-input').value.trim();
    if (code) fetchAndDisplayToken(code);
  });
}

function openTokenDetailModal(tokenCode) {
  // Navigate directly to Track Token in Farmer Portal and fetch token
  const farmerTab = document.getElementById('tab-farmer');
  if (farmerTab) farmerTab.click();

  const trackSubTab = document.querySelector('[data-subtarget="farmer-track"]');
  if (trackSubTab) trackSubTab.click();

  const input = document.getElementById('track-token-input');
  if (input) input.value = tokenCode;

  fetchAndDisplayToken(tokenCode);
}

async function fetchAndDisplayToken(tokenCode) {
  try {
    const res = await fetch(`/api/farmer/tokens/${tokenCode}`);
    if (!res.ok) {
      showToast('Token Not Found', `No booking record found for ${tokenCode}`, 'warning');
      return;
    }
    const token = await res.json();
    state.activeTokenData = token;

    // Update Token Card Texts
    document.getElementById('token-code-text').innerText = token.token_code;
    document.getElementById('token-center-text').innerText = `${token.center_name} (${token.center_district})`;
    document.getElementById('token-farmer-text').innerText = `${token.farmer_name} (${token.farmer_phone})`;
    document.getElementById('token-crop-weight-text').innerText = `${token.crop_name} - ${token.allocated_weight_q} Q (Tranche ${token.tranche_number}/${token.total_tranches})`;
    document.getElementById('token-window-text').innerText = `${token.arrival_window_start} - ${token.arrival_window_end} (${token.scheduled_date})`;
    document.getElementById('token-tractor-text').innerText = token.tractor_number || 'N/A';

    // Status Badge
    const statusBadge = document.getElementById('token-status-badge');
    statusBadge.innerText = token.status;
    statusBadge.className = `badge ${token.status === 'PAYMENT_DISPATCHED' ? 'badge-safe' : token.status === 'REJECTED' ? 'badge-critical' : 'badge-info'}`;

    // Generate QR Code
    const qrContainer = document.getElementById('qrcode-box');
    qrContainer.innerHTML = '';
    new QRCode(qrContainer, {
      text: token.qr_payload || JSON.stringify({ token: token.token_code, farmer: token.farmer_name, crop: token.crop_name }),
      width: 140,
      height: 140,
      colorDark: '#000000',
      colorLight: '#ffffff',
      correctLevel: QRCode.CorrectLevel.M
    });

    // Update 5-Stage Stepper
    updateStepper(token.status);

    // Render Journey details
    const detailsContainer = document.getElementById('token-live-details');
    let detailsHtml = `
      <div style="display:flex; justify-content:space-between; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem;">
        <span style="color:var(--text-muted);">Current Status:</span>
        <strong style="color:#ffffff;">${token.status}</strong>
      </div>
      <div style="display:flex; justify-content:space-between; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem;">
        <span style="color:var(--text-muted);">Assigned Window:</span>
        <span>${token.arrival_window_start} - ${token.arrival_window_end}</span>
      </div>
    `;

    if (token.quality_inspection) {
      const qi = token.quality_inspection;
      detailsHtml += `
        <div style="display:flex; justify-content:space-between; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem;">
          <span style="color:var(--text-muted);">AI Quality Grade:</span>
          <span style="color:#34d399; font-weight:700;">Grade ${qi.final_grade} (Moisture: ${qi.moisture_percentage}%)</span>
        </div>
      `;
    }

    if (token.weighment) {
      const w = token.weighment;
      detailsHtml += `
        <div style="display:flex; justify-content:space-between; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem;">
          <span style="color:var(--text-muted);">Official Net Weight:</span>
          <span style="font-weight:700;">${w.net_weight_q} Q (Gross: ${w.gross_weight_q}Q, Tare: ${w.tare_weight_q}Q)</span>
        </div>
      `;
    }

    if (token.receipt && token.payment) {
      detailsHtml += `
        <div style="display:flex; justify-content:space-between; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem;">
          <span style="color:var(--text-muted);">Net Payout (DBT):</span>
          <span style="color:#34d399; font-size:1.1rem; font-weight:800;">₹${token.receipt.net_payable_amount.toLocaleString('en-IN')}</span>
        </div>
        <div style="font-size:0.75rem; color:var(--text-muted);">
          DBT Reference: <strong>${token.payment.transaction_ref}</strong>
        </div>
      `;
      document.getElementById('receipt-action-box').style.display = 'block';
      document.getElementById('btn-view-receipt').onclick = () => showReceiptModal(token);
    } else {
      document.getElementById('receipt-action-box').style.display = 'none';
    }

    detailsContainer.innerHTML = detailsHtml;

  } catch (err) {
    console.error('Fetch token error:', err);
  }
}

function updateStepper(status) {
  const steps = ['confirmed', 'checked-in', 'quality', 'weighment', 'payment'];
  const statusMap = {
    'CONFIRMED': 0,
    'CHECKED_IN': 1,
    'QUALITY_APPROVED': 2,
    'WEIGHMENT_COMPLETE': 3,
    'PAYMENT_DISPATCHED': 4,
    'REJECTED': -1
  };

  const activeIndex = statusMap[status] !== undefined ? statusMap[status] : 0;

  steps.forEach((s, idx) => {
    const el = document.getElementById(`step-${s}`);
    if (!el) return;
    el.className = 'stepper-step';

    if (activeIndex === -1) {
      // Rejected
      if (idx === 0) el.classList.add('completed');
    } else if (idx < activeIndex) {
      el.classList.add('completed');
    } else if (idx === activeIndex) {
      el.classList.add('active');
    }
  });
}

function showReceiptModal(token) {
  const r = token.receipt;
  if (!r) return;

  document.getElementById('rec-number').innerText = r.receipt_number;
  document.getElementById('rec-token').innerText = token.token_code;
  document.getElementById('rec-date').innerText = new Date(r.created_at || Date.now()).toISOString().split('T')[0];
  document.getElementById('rec-center').innerText = token.center_name;
  document.getElementById('rec-farmer').innerText = token.farmer_name;
  document.getElementById('rec-phone').innerText = token.farmer_phone;
  document.getElementById('rec-crop').innerText = `${token.crop_name} (${token.quality_inspection ? 'Grade ' + token.quality_inspection.final_grade : 'FAQ'})`;

  document.getElementById('rec-table-desc').innerText = `${token.crop_name} FAQ Procurement (MSP Rate)`;
  document.getElementById('rec-table-weight').innerText = `${r.final_weight_q} Q`;
  document.getElementById('rec-table-rate').innerText = `₹${r.msp_rate_per_q.toLocaleString('en-IN')}`;
  document.getElementById('rec-table-gross').innerText = `₹${r.gross_amount.toLocaleString('en-IN')}`;
  document.getElementById('rec-table-deductions').innerText = `-₹${(r.quality_deductions || 0).toLocaleString('en-IN')}`;
  document.getElementById('rec-table-net').innerText = `₹${r.net_payable_amount.toLocaleString('en-IN')}`;
  document.getElementById('rec-txn-ref').innerText = r.transaction_ref;

  document.getElementById('receipt-modal').style.display = 'flex';
}

// -----------------------------------------------------------------------------
// 2. AI MOISTURE PRE-SCREENING LOGIC
// -----------------------------------------------------------------------------
async function runPreScreenSimulation(sampleType) {
  try {
    const formData = new FormData();
    formData.append('crop_name', state.selectedCrop);
    formData.append('sample_type', sampleType);

    const res = await fetch('/api/farmer/pre-screening', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    renderPreScreenResult(result);
  } catch (err) {
    console.error('Pre screen error:', err);
  }
}

function renderPreScreenResult(res) {
  document.getElementById('ai-moisture-val').innerText = `${res.moisture_percentage}%`;
  document.getElementById('ai-discolor-val').innerText = `${res.discoloration_percentage}%`;
  document.getElementById('ai-foreign-val').innerText = `${res.foreign_matter_percentage}%`;
  document.getElementById('ai-broken-val').innerText = `${res.broken_grains_percentage}%`;

  const badge = document.getElementById('ai-grade-badge');
  badge.innerText = res.grade_label;
  if (res.ai_grade === 'A') {
    badge.className = 'badge badge-safe';
    document.getElementById('ai-recommendation-box').style.borderLeftColor = '#10b981';
    document.getElementById('ai-moisture-val').style.color = '#34d399';
  } else if (res.ai_grade === 'B') {
    badge.className = 'badge badge-warning';
    document.getElementById('ai-recommendation-box').style.borderLeftColor = '#f59e0b';
    document.getElementById('ai-moisture-val').style.color = '#fbbf24';
  } else {
    badge.className = 'badge badge-critical';
    document.getElementById('ai-recommendation-box').style.borderLeftColor = '#ef4444';
    document.getElementById('ai-moisture-val').style.color = '#f87171';
  }

  document.getElementById('ai-recommendation-text').innerText = `${res.outcome} ${res.recommendation}`;
  showToast('AI Quality Assessed', `Grade: ${res.grade_label} (Moisture: ${res.moisture_percentage}%)`, res.ai_grade === 'REJECTED' ? 'danger' : 'safe');
}

// -----------------------------------------------------------------------------
// 3. FARMER HISTORY & SMS NOTIFICATIONS LOGIC
// -----------------------------------------------------------------------------
async function loadFarmerHistory() {
  const phone = document.getElementById('book-phone').value.trim() || '9876543210';

  try {
    // 1. Fetch SMS Notifications
    const noteRes = await fetch(`/api/farmer/notifications/${phone}`);
    const notes = await noteRes.json();
    const smsBox = document.getElementById('sms-inbox-list');
    smsBox.innerHTML = '';

    if (!notes.length) {
      smsBox.innerHTML = '<p style="color:var(--text-dim); font-size:0.85rem;">No SMS notifications sent yet.</p>';
    } else {
      notes.forEach((n) => {
        const item = document.createElement('div');
        item.className = 'glass-card';
        item.style.padding = '0.75rem';
        item.innerHTML = `
          <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-muted); margin-bottom:0.25rem;">
            <strong>${n.title}</strong>
            <span>${new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          </div>
          <div style="font-size:0.8rem; color:#ffffff;">${n.message}</div>
        `;
        smsBox.appendChild(item);
      });
    }

    // 2. Fetch Past Receipts
    const histRes = await fetch(`/api/farmer/history/${phone}`);
    const hist = await histRes.json();
    const recBox = document.getElementById('farmer-receipts-list');
    recBox.innerHTML = '';

    if (!hist.receipts || !hist.receipts.length) {
      recBox.innerHTML = '<p style="color:var(--text-dim); font-size:0.85rem;">No completed procurement receipts yet.</p>';
    } else {
      hist.receipts.forEach((r) => {
        const item = document.createElement('div');
        item.className = 'glass-card';
        item.style.padding = '0.75rem';
        item.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.25rem;">
            <strong style="color:#ffffff;">${r.receipt_number}</strong>
            <span class="badge badge-safe">₹${r.net_payable_amount.toLocaleString('en-IN')}</span>
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted);">
            Crop: ${r.crop_name} (${r.final_weight_q} Q) • ${r.center_name}<br>
            DBT Ref: ${r.transaction_ref}
          </div>
        `;
        recBox.appendChild(item);
      });
    }
  } catch (err) {
    console.error('Load history error:', err);
  }
}

// -----------------------------------------------------------------------------
// 4. SECURITY GUARD / GATEKEEPER LOGIC (OFFLINE-FIRST)
// -----------------------------------------------------------------------------
async function refreshGuardManifest() {
  try {
    const res = await fetch('/api/guard/offline-manifest/1');
    if (res.ok) {
      const data = await res.json();
      await window.offlineStorage.cacheManifest(data.bookings);
      showToast('Offline Manifest Cached', `Cached ${data.total_bookings} center bookings for offline gate operations.`, 'safe');
    }
  } catch (err) {
    console.warn('Could not refresh online manifest, running with local IndexedDB cache.');
  }
  updateGuardSyncCount();
}

function scanTokenDemo(tokenCode) {
  document.getElementById('guard-token-input').value = tokenCode;
  verifyGuardToken(tokenCode);
}

async function verifyGuardToken(tokenCode) {
  const resultBody = document.getElementById('guard-result-body');
  const actionBox = document.getElementById('guard-action-box');
  const isOnline = window.offlineStorage.getEffectiveOnlineStatus();

  let booking = null;

  if (isOnline) {
    try {
      const res = await fetch(`/api/guard/verify-token/${tokenCode}`);
      if (res.ok) {
        booking = await res.json();
      }
    } catch (e) {
      console.warn('Online verify failed, falling back to IndexedDB manifest.');
    }
  }

  // Fallback to offline IndexedDB manifest
  if (!booking) {
    booking = await window.offlineStorage.lookupOfflineBooking(tokenCode);
    if (booking) {
      booking.can_check_in = booking.status === 'CONFIRMED';
      booking.arrival_window = `${booking.arrival_window_start} - ${booking.arrival_window_end}`;
    }
  }

  if (!booking) {
    resultBody.innerHTML = `<p style="color:#f87171;">❌ Token '${tokenCode}' not found in online server or offline cached manifest.</p>`;
    actionBox.style.display = 'none';
    return;
  }

  resultBody.innerHTML = `
    <div style="background:rgba(15,23,42,0.7); padding:1rem; border-radius:var(--radius-sm);">
      <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
        <strong style="font-size:1.1rem; color:#ffffff;">${booking.farmer_name}</strong>
        <span class="badge ${booking.status === 'CONFIRMED' ? 'badge-safe' : 'badge-info'}">${booking.status}</span>
      </div>
      <div style="font-size:0.8rem; color:var(--text-muted); display:grid; grid-template-columns:1fr 1fr; gap:0.4rem;">
        <div>Mobile: <span style="color:#ffffff;">${booking.farmer_phone}</span></div>
        <div>Village: <span style="color:#ffffff;">${booking.farmer_village || 'Local'}</span></div>
        <div>Crop: <span style="color:#ffffff;">${booking.crop_name} (${booking.allocated_weight_q} Q)</span></div>
        <div>Arrival Slot: <span style="color:#ffffff;">${booking.arrival_window}</span></div>
      </div>
    </div>
  `;

  if (booking.can_check_in || booking.status === 'CONFIRMED') {
    actionBox.style.display = 'block';
    document.getElementById('guard-tractor-input').value = booking.tractor_number || 'UP-65-AB-1234';

    document.getElementById('btn-gate-checkin').onclick = () => executeGateCheckIn(booking.token_code);
  } else {
    actionBox.style.display = 'none';
  }
}

async function executeGateCheckIn(tokenCode) {
  const isOnline = window.offlineStorage.getEffectiveOnlineStatus();
  const tractorNo = document.getElementById('guard-tractor-input').value.trim();

  if (isOnline) {
    // Online check-in
    try {
      const res = await fetch('/api/guard/check-in', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token_code: tokenCode, tractor_number: tractorNo })
      });
      const data = await res.json();
      showToast('Gate Check-In Approved', `Farmer checked-in online. Token ${tokenCode} advanced to Mandi Queue.`, 'safe');
      verifyGuardToken(tokenCode);
    } catch (e) {
      console.warn('Online checkin call failed, falling back to local queue.');
      queueOfflineCheckInLocal(tokenCode, tractorNo);
    }
  } else {
    // Pure Offline check-in
    await queueOfflineCheckInLocal(tokenCode, tractorNo);
  }
}

async function queueOfflineCheckInLocal(tokenCode, tractorNo) {
  const txItem = await window.offlineStorage.queueOfflineCheckIn(tokenCode, tractorNo);
  showToast('Offline Check-In Queued', `Recorded in local IndexedDB. Sync will occur automatically on reconnection.`, 'warning');
  verifyGuardToken(tokenCode);
  updateGuardSyncCount();
}

async function updateGuardSyncCount() {
  const pending = await window.offlineStorage.getPendingTransactions();
  const countEl = document.getElementById('guard-pending-count');
  if (countEl) countEl.innerText = pending.length;

  const tableBody = document.getElementById('guard-sync-table-body');
  if (!tableBody) return;

  if (!pending.length) {
    tableBody.innerHTML = `<tr><td colspan="5" style="padding: 1rem; text-align: center; color: var(--text-dim);">No pending offline transactions. Terminal in sync with central server.</td></tr>`;
  } else {
    tableBody.innerHTML = '';
    pending.forEach((p) => {
      const row = document.createElement('tr');
      row.style.borderBottom = '1px solid var(--border)';
      row.innerHTML = `
        <td style="padding: 0.5rem; font-family: monospace;">${p.client_tx_id}</td>
        <td style="padding: 0.5rem; font-weight: 700; color: #ffffff;">${p.token_code}</td>
        <td style="padding: 0.5rem;">${p.sync_type}</td>
        <td style="padding: 0.5rem; color: var(--text-muted);">${new Date(p.client_timestamp).toLocaleTimeString()}</td>
        <td style="padding: 0.5rem;"><span class="badge badge-warning">Pending Sync</span></td>
      `;
      tableBody.appendChild(row);
    });
  }
}

function setupGuardEvents() {
  document.getElementById('btn-guard-verify').addEventListener('click', () => {
    const code = document.getElementById('guard-token-input').value.trim();
    if (code) verifyGuardToken(code);
  });

  document.getElementById('btn-refresh-manifest').addEventListener('click', refreshGuardManifest);

  document.getElementById('btn-sync-offline-queue').addEventListener('click', async () => {
    const res = await window.offlineStorage.syncPendingTransactions();
    if (res.status === 'success') {
      showToast('Sync Successful', res.message, 'safe');
      updateGuardSyncCount();
    } else {
      showToast('Sync Status', res.message, res.status === 'offline' ? 'warning' : 'info');
    }
  });
}

// -----------------------------------------------------------------------------
// 5. MANDI CLERK & QUALITY INSPECTOR LOGIC
// -----------------------------------------------------------------------------
let allClerkSlotsCache = [];

async function loadClerkQueue(showFeedback = false) {
  const centerSelect = document.getElementById('clerk-center-select');
  const centerId = (centerSelect && centerSelect.value) ? centerSelect.value : 'ALL';
  const refreshBtn = document.getElementById('btn-refresh-clerk-queue');
  
  if (refreshBtn) {
    refreshBtn.disabled = true;
    refreshBtn.innerText = '⏳ Syncing...';
  }

  try {
    const res = await fetch(`/api/clerk/queue/${centerId}`);
    if (!res.ok) {
      console.error('Clerk queue fetch failed:', res.status);
      showToast('Sync Error', 'Could not retrieve latest PACS queue data.', 'danger');
      return;
    }
    const queue = await res.json();
    allClerkSlotsCache = queue;
    renderClerkQueue(queue);

    if (showFeedback) {
      showToast('Pipeline Synced', `Loaded ${queue.length} tokens for ${centerId === 'ALL' ? 'All Centers' : 'Selected PACS'}.`, 'safe');
    }
  } catch (err) {
    console.error('Clerk queue error:', err);
    showToast('Sync Error', 'Database connection error.', 'danger');
  } finally {
    if (refreshBtn) {
      refreshBtn.disabled = false;
      refreshBtn.innerText = '🔄 Refresh Pipeline';
    }
  }
}

function renderClerkQueue(queue) {
  const activeTbody = document.getElementById('clerk-queue-table-body');
  const historyTbody = document.getElementById('clerk-history-table-body');
  const searchInput = document.getElementById('clerk-search-input');
  const query = searchInput ? searchInput.value.trim().toLowerCase() : '';

  if (activeTbody) activeTbody.innerHTML = '';
  if (historyTbody) historyTbody.innerHTML = '';

  let filtered = queue;
  if (query) {
    filtered = queue.filter(s => 
      (s.token_code && s.token_code.toLowerCase().includes(query)) ||
      (s.farmer_name && s.farmer_name.toLowerCase().includes(query)) ||
      (s.farmer_phone && s.farmer_phone.toLowerCase().includes(query)) ||
      (s.crop_name && s.crop_name.toLowerCase().includes(query)) ||
      (s.receipt_number && s.receipt_number.toLowerCase().includes(query)) ||
      (s.center_name && s.center_name.toLowerCase().includes(query))
    );
  }

  const activeSlots = filtered.filter(s => s.status !== 'PAYMENT_DISPATCHED' && s.status !== 'FULFILLED');
  const completedSlots = filtered.filter(s => s.status === 'PAYMENT_DISPATCHED' || s.status === 'FULFILLED');

  const activeCountEl = document.getElementById('clerk-active-count');
  if (activeCountEl) activeCountEl.innerText = `${activeSlots.length} ACTIVE`;

  const historyCountEl = document.getElementById('clerk-history-count');
  if (historyCountEl) historyCountEl.innerText = `${completedSlots.length} COMPLETED`;

  // 1. Render Active Queue
  if (activeTbody) {
    if (!activeSlots.length) {
      activeTbody.innerHTML = `<tr><td colspan="7" style="padding: 1.5rem; text-align: center; color: var(--text-dim);">No active farmer deliveries waiting in queue.</td></tr>`;
    } else {
      activeSlots.forEach((s) => {
        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid var(--border)';
        row.innerHTML = `
          <td style="padding: 0.75rem; font-weight: 700; color: #ffffff; font-family: var(--font-mono);">
            ${s.token_code}
            <button class="btn btn-secondary btn-sm" onclick="openTokenDetailModal('${s.token_code}')" style="padding: 0.15rem 0.4rem; font-size: 0.65rem; margin-left: 0.35rem;" title="View Token Details">🎫</button>
          </td>
          <td style="padding: 0.75rem;">
            <strong>${s.farmer_name}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${s.center_name || 'Rampur PACS'} • ${s.farmer_phone}</div>
          </td>
          <td style="padding: 0.75rem;">
            <span class="badge badge-info">${s.crop_name}</span>
            <span style="font-weight: 600; font-size: 0.85rem; margin-left: 0.3rem;">${s.allocated_weight_q} Q</span>
          </td>
          <td style="padding: 0.75rem; color: var(--text-muted); font-size: 0.85rem;">
            ${s.scheduled_date || 'Today'} • ${s.arrival_window_start || '08:00'} - ${s.arrival_window_end || '10:00'}
          </td>
          <td style="padding: 0.75rem; font-family: var(--font-mono); font-size: 0.85rem;">${s.tractor_number || 'UP-65-AB-1234'}</td>
          <td style="padding: 0.75rem;">
            <span class="badge ${s.status === 'CHECKED_IN' ? 'badge-safe' : 'badge-warning'}">${s.status}</span>
          </td>
          <td style="padding: 0.75rem;">
            <button class="btn btn-primary btn-sm" onclick='openClerkInspectionModal(${JSON.stringify(s)})'>
              🔍 Inspect & Weigh
            </button>
          </td>
        `;
        activeTbody.appendChild(row);
      });
    }
  }

  // 2. Render Completed History & DBT Dispatches Table
  if (historyTbody) {
    if (!completedSlots.length) {
      historyTbody.innerHTML = `<tr><td colspan="7" style="padding: 1.5rem; text-align: center; color: var(--text-dim);">No completed procurements recorded yet.</td></tr>`;
    } else {
      completedSlots.forEach((s) => {
        const netAmt = s.net_payable_amount ? `₹${parseFloat(s.net_payable_amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}` : '₹0.00';
        const recNo = s.receipt_number || 'REC-PENDING';
        
        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid var(--border)';
        row.innerHTML = `
          <td style="padding: 0.75rem; font-weight: 700; color: #ffffff; font-family: var(--font-mono);">${s.token_code}</td>
          <td style="padding: 0.75rem;">
            <strong>${s.farmer_name}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${s.center_name || 'Rampur PACS'} • ${s.farmer_phone}</div>
          </td>
          <td style="padding: 0.75rem;">
            <span class="badge badge-info">${s.crop_name}</span>
            <span style="font-weight: 700; font-size: 0.85rem; margin-left: 0.3rem;">${s.allocated_weight_q} Q</span>
          </td>
          <td style="padding: 0.75rem; font-weight: 800; color: #34d399; font-size: 0.95rem;">${netAmt}</td>
          <td style="padding: 0.75rem; font-family: var(--font-mono); font-size: 0.85rem; color: #94a3b8;">${recNo}</td>
          <td style="padding: 0.75rem;"><span class="badge badge-safe">DISPATCHED</span></td>
          <td style="padding: 0.75rem; display: flex; gap: 0.35rem; align-items: center;">
            <button class="btn btn-secondary btn-sm" onclick="openTokenDetailModal('${s.token_code}')" style="padding: 0.3rem 0.6rem; font-size: 0.75rem;">
              🎫 View Token
            </button>
            <button class="btn btn-primary btn-sm" onclick="viewReceiptByToken('${s.token_code}')" style="padding: 0.3rem 0.6rem; font-size: 0.75rem; background: linear-gradient(135deg, #059669, #047857);">
              🧾 View Receipt
            </button>
          </td>
        `;
        historyTbody.appendChild(row);
      });
    }
  }
}

async function viewReceiptByToken(tokenCode) {
  try {
    const res = await fetch(`/api/farmer/tokens/${tokenCode}`);
    if (res.ok) {
      const fullToken = await res.json();
      if (fullToken.receipt) {
        showReceiptModal(fullToken);
      } else {
        showToast('Receipt Pending', 'Receipt is being finalized by bank DBT network.', 'info');
      }
    } else {
      showToast('Error', 'Could not load receipt details.', 'danger');
    }
  } catch (err) {
    console.error('View receipt error:', err);
    showToast('Error', 'Failed to retrieve receipt.', 'danger');
  }
}

function openClerkInspectionModal(slot) {
  state.activeClerkSlot = slot;
  const panel = document.getElementById('clerk-inspection-panel');
  panel.style.display = 'block';

  document.getElementById('clerk-active-token').innerText = slot.token_code;
  document.getElementById('clerk-farmer-name').innerText = `${slot.farmer_name} - ${slot.crop_name} (${slot.allocated_weight_q} Q)`;

  // Set default gross & tare
  const alloc = slot.allocated_weight_q || 32.0;
  document.getElementById('clerk-gross-weight').value = alloc + 20.0;
  document.getElementById('clerk-tare-weight').value = 20.0;
  document.getElementById('clerk-estimated-weight-text').innerText = `${alloc} Q`;

  calculateClerkNetWeight();

  // Scroll to panel
  panel.scrollIntoView({ behavior: 'smooth' });
}

const CLERK_MSP_TABLE = {
  'Wheat': 2275.0,
  'Paddy': 2183.0,
  'Chana': 5440.0,
  'Tur': 7000.0,
  'Mustard': 5650.0,
  'Maize': 2090.0,
  'Moong': 8558.0,
  'Urad': 6950.0,
  'Soybean': 4600.0,
  'Groundnut': 6377.0
};

function calculateClerkNetWeight() {
  const gross = parseFloat(document.getElementById('clerk-gross-weight').value) || 0;
  const tare = parseFloat(document.getElementById('clerk-tare-weight').value) || 0;
  const net = Math.max(0, gross - tare);

  document.getElementById('clerk-net-weight-text').innerText = `${net.toFixed(1)} Q`;

  const slot = state.activeClerkSlot;
  const estimated = slot ? slot.allocated_weight_q : net;

  const dev = estimated > 0 ? (((net - estimated) / estimated) * 100).toFixed(1) : 0;
  const isMismatch = Math.abs(dev) > 15.0;

  const tolText = document.getElementById('clerk-tolerance-text');
  if (isMismatch) {
    tolText.style.color = '#f87171';
    tolText.innerText = `${dev}% (WARNING: Exceeds ±15% tolerance)`;
  } else {
    tolText.style.color = '#34d399';
    tolText.innerText = `${dev}% (Normal within ±15%)`;
  }

  // Real-time MSP, Gross, Deductions, and Net DBT Payout Calculation
  const crop = (slot && slot.crop_name) ? slot.crop_name : 'Wheat';
  const mspRate = CLERK_MSP_TABLE[crop] || 2275.0;
  
  const moisture = parseFloat(document.getElementById('clerk-moisture').value) || 12.0;
  const isOverride = document.getElementById('clerk-override-toggle').checked;
  const overrideGrade = document.getElementById('clerk-override-grade').value;
  const aiGrade = moisture < 14.5 ? 'A' : moisture <= 16.5 ? 'B' : 'REJECTED';
  const finalGrade = isOverride ? overrideGrade : aiGrade;

  const gradeBadge = document.getElementById('clerk-ai-grade-badge');
  if (gradeBadge) {
    gradeBadge.innerText = `Grade ${finalGrade}`;
    gradeBadge.className = `badge ${finalGrade === 'A' ? 'badge-safe' : finalGrade === 'B' ? 'badge-warning' : 'badge-critical'}`;
  }

  const grossVal = net * mspRate;
  let deductionRate = 0.0;
  let deductionReason = 'Grade A: 0% deduction (Prime Quality)';

  if (finalGrade === 'B') {
    deductionRate = 0.01; // 1.0% standard moisture refraction
    deductionReason = 'Grade B: -1.0% Standard Refraction deduction';
  } else if (finalGrade === 'REJECTED') {
    deductionRate = 1.0;
    deductionReason = 'REJECTED: Moisture > 16.5% / Quality non-compliant';
  }

  const deductionVal = finalGrade === 'REJECTED' ? grossVal : (grossVal * deductionRate);
  const netPayable = Math.max(0, grossVal - deductionVal);

  const mspBadge = document.getElementById('clerk-msp-rate-badge');
  if (mspBadge) mspBadge.innerText = `${crop} MSP: ₹${mspRate.toLocaleString('en-IN')} / Q`;

  const grossEl = document.getElementById('clerk-calc-gross');
  if (grossEl) grossEl.innerText = `₹${grossVal.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

  const deductEl = document.getElementById('clerk-calc-deductions');
  if (deductEl) deductEl.innerText = `-₹${deductionVal.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

  const reasonEl = document.getElementById('clerk-deduction-reason');
  if (reasonEl) reasonEl.innerText = deductionReason;

  const netEl = document.getElementById('clerk-calc-net');
  if (netEl) netEl.innerText = `₹${netPayable.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

  const btnAmount = document.getElementById('clerk-btn-amount');
  if (btnAmount) btnAmount.innerText = `₹${netPayable.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
}

async function executeClerkAcceptFulfill() {
  const slot = state.activeClerkSlot;
  if (!slot) return;

  const gross = parseFloat(document.getElementById('clerk-gross-weight').value);
  const tare = parseFloat(document.getElementById('clerk-tare-weight').value);
  const moisture = parseFloat(document.getElementById('clerk-moisture').value);
  const discolor = parseFloat(document.getElementById('clerk-discolor').value);
  const foreign = parseFloat(document.getElementById('clerk-foreign').value);
  const broken = parseFloat(document.getElementById('clerk-broken').value);

  const isOverride = document.getElementById('clerk-override-toggle').checked;
  const overrideGrade = document.getElementById('clerk-override-grade').value;
  const overrideReason = document.getElementById('clerk-override-reason').value;
  const notes = document.getElementById('clerk-notes').value;

  const aiGrade = moisture < 14.5 ? 'A' : moisture <= 16.5 ? 'B' : 'REJECTED';
  const finalGrade = isOverride ? overrideGrade : aiGrade;

  try {
    const res = await fetch('/api/clerk/accept-and-fulfill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token_code: slot.token_code,
        gross_weight_q: gross,
        tare_weight_q: tare,
        moisture_percentage: moisture,
        discoloration_percentage: discolor,
        foreign_matter_percentage: foreign,
        broken_grains_percentage: broken,
        ai_grade: aiGrade,
        is_manual_override: isOverride,
        override_reason: overrideReason,
        final_grade: finalGrade,
        inspector_notes: notes
      })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast('Error', data.detail || 'Fulfillment failed.', 'danger');
      return;
    }

    showToast('Procurement Fulfilled!', `Receipt ${data.receipt_number} generated. Payout ₹${data.payment_breakdown.net_payable_amount.toLocaleString('en-IN')} dispatched.`, 'safe');
    document.getElementById('clerk-inspection-panel').style.display = 'none';
    
    // Refresh Clerk Queue and Procurement Centers
    await loadClerkQueue(false);
    loadProcurementCenters();

    // Automatically open the Official Electronic Receipt Modal on its own!
    await viewReceiptByToken(slot.token_code);

  } catch (err) {
    console.error('Accept fulfill error:', err);
  }
}

async function triggerClerkReject() {
  const slot = state.activeClerkSlot;
  if (!slot) return;

  const reason = prompt('Enter Rejection Reason (e.g. Moisture > 16.5% excess wetness / high foreign matter):', 'Excessive moisture content detected (>16.5%). High spoilage risk.');
  if (!reason) return;

  try {
    const res = await fetch('/api/clerk/reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token_code: slot.token_code,
        rejection_reason: reason,
        recommendation: 'Sun dry grain for 2-3 days before returning to mandi.'
      })
    });

    if (res.ok) {
      showToast('Delivery Rejected', `Token ${slot.token_code} marked REJECTED and quota released.`, 'warning');
      document.getElementById('clerk-inspection-panel').style.display = 'none';
      loadClerkQueue();
    }
  } catch (err) {
    console.error('Reject error:', err);
  }
}

function setupClerkEvents() {
  const centerSelect = document.getElementById('clerk-center-select');
  if (centerSelect) centerSelect.addEventListener('change', () => loadClerkQueue(false));

  const refreshBtn = document.getElementById('btn-refresh-clerk-queue');
  if (refreshBtn) refreshBtn.addEventListener('click', () => loadClerkQueue(true));

  const searchInput = document.getElementById('clerk-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      renderClerkQueue(allClerkSlotsCache);
    });
  }

  const overrideToggle = document.getElementById('clerk-override-toggle');
  if (overrideToggle) {
    overrideToggle.addEventListener('change', (e) => {
      const box = document.getElementById('clerk-override-box');
      if (box) box.style.display = e.target.checked ? 'block' : 'none';
      calculateClerkNetWeight();
    });
  }

  const overrideGrade = document.getElementById('clerk-override-grade');
  if (overrideGrade) {
    overrideGrade.addEventListener('change', calculateClerkNetWeight);
  }

  ['clerk-moisture', 'clerk-discolor', 'clerk-foreign', 'clerk-broken'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', calculateClerkNetWeight);
  });
}

// -----------------------------------------------------------------------------
// 6. DISTRICT ADMIN / DOCA COMMAND CENTER LOGIC
// -----------------------------------------------------------------------------
async function loadAdminDashboard() {
  try {
    // 1. Top Level Metrics
    const mRes = await fetch('/api/admin/metrics');
    const m = await mRes.json();
    document.getElementById('kpi-farmers').innerText = m.total_farmers;
    document.getElementById('kpi-small-farmers').innerText = `${m.small_farmer_percentage}% Smallholders Protected`;
    document.getElementById('kpi-bookings').innerText = m.total_bookings;
    document.getElementById('kpi-pending').innerText = `${m.pending_arrival} Pending Gate Arrival`;
    document.getElementById('kpi-checkedin').innerText = m.checked_in;
    document.getElementById('kpi-completed').innerText = m.completed;
    document.getElementById('kpi-procured-q').innerText = m.total_procured_q.toFixed(1);
    document.getElementById('kpi-payout-cr').innerText = `₹${m.total_payout_crores.toFixed(2)} Cr`;

    // 2. Centers Storage Grid
    const cRes = await fetch('/api/admin/centers');
    const centers = await cRes.json();
    renderAdminCenters(centers);

    // 3. Evacuation Alerts
    const aRes = await fetch('/api/admin/evacuation-alerts');
    const alerts = await aRes.json();
    renderAdminAlerts(alerts);

    // 4. System Intelligence
    loadSystemIntelligence('queue');

  } catch (err) {
    console.error('Admin load error:', err);
  }
}

function renderAdminCenters(centers) {
  const container = document.getElementById('admin-centers-grid');
  container.innerHTML = '';

  centers.forEach((c) => {
    const card = document.createElement('div');
    card.className = 'glass-card';

    let badgeClass = 'badge-safe';
    if (c.storage_state === 'Warning') badgeClass = 'badge-warning';
    if (c.storage_state === 'Critical') badgeClass = 'badge-critical';

    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.5rem;">
        <div>
          <h4 style="font-size:1.05rem; color:#ffffff;">${c.name}</h4>
          <div style="font-size:0.75rem; color:var(--text-muted);">${c.code} • ${c.district}</div>
        </div>
        <span class="badge ${badgeClass}">${c.storage_state} (${c.s_fill_percentage}%)</span>
      </div>

      <div class="storage-bar-container" style="margin:0.75rem 0;">
        <div class="storage-bar-fill storage-${c.storage_state.toLowerCase()}" style="width:${Math.min(100, c.s_fill_percentage)}%;"></div>
      </div>

      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem; font-size:0.75rem; color:var(--text-muted); margin-bottom:0.75rem;">
        <div>Current Stock: <strong style="color:#ffffff;">${c.current_stock_q} Q</strong></div>
        <div>Incoming Booked: <strong style="color:#ffffff;">${c.incoming_booked_q} Q</strong></div>
        <div>Max Capacity: <strong style="color:#ffffff;">${c.max_capacity_q} Q</strong></div>
        <div>Headroom Left: <strong style="color:#34d399;">${c.available_headroom_q} Q</strong></div>
      </div>

      <div style="display:flex; justify-content:space-between; font-size:0.75rem; border-top:1px solid var(--border); padding-top:0.5rem;">
        <span>Live Gate Queue: <strong>${c.live_queue_count}</strong></span>
        <span>Procured Today: <strong>${c.procured_count}</strong></span>
      </div>
    `;
    container.appendChild(card);
  });
}

function renderAdminAlerts(alerts) {
  const container = document.getElementById('admin-alerts-container');
  const countBadge = document.getElementById('admin-alerts-count');
  container.innerHTML = '';

  const activeAlerts = alerts.filter(a => a.status === 'ACTIVE');
  countBadge.innerText = `${activeAlerts.length} Active Alert${activeAlerts.length !== 1 ? 's' : ''}`;
  countBadge.className = activeAlerts.length ? 'badge badge-warning badge-pulse' : 'badge badge-safe';

  if (!alerts.length) {
    container.innerHTML = '<p style="color:var(--text-dim); font-size:0.85rem;">No evacuation alerts active across the district.</p>';
    return;
  }

  alerts.forEach((a) => {
    const card = document.createElement('div');
    card.className = 'glass-card';
    card.style.borderColor = a.status === 'ACTIVE' ? 'var(--warning)' : 'var(--border)';

    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
        <div>
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <span class="badge ${a.status === 'ACTIVE' ? 'badge-warning' : 'badge-safe'}">${a.status}</span>
            <strong style="color:#ffffff; font-size:0.95rem;">${a.center_name} (${a.current_fill_percentage}% Full)</strong>
          </div>
          <p style="font-size:0.8rem; color:var(--text-muted); margin-top:0.25rem;">
            ${a.trigger_reason} • Recommended Evacuation Destination: <strong>${a.recommended_destination}</strong>
          </p>
        </div>
        <div>
          ${a.status === 'ACTIVE' ? `
            <button class="btn btn-primary btn-sm" onclick="dispatchEvacuationAlert(${a.id}, ${a.recommended_trucks})">
              🚚 Dispatch ${a.recommended_trucks} Trucks (${a.recommended_trucks * 10} MT)
            </button>
          ` : `
            <span style="font-size:0.8rem; color:#34d399; font-weight:700;">✓ Fleet Dispatched</span>
          `}
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

async function dispatchEvacuationAlert(alertId, trucks) {
  try {
    const res = await fetch(`/api/admin/evacuation-alerts/${alertId}/dispatch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trucks_dispatched: trucks })
    });
    if (res.ok) {
      showToast('Evacuation Dispatched', `State logistics fleet of ${trucks} trucks dispatched. Godown stock balanced.`, 'safe');
      loadAdminDashboard();
    }
  } catch (err) {
    console.error('Dispatch error:', err);
  }
}

async function loadSystemIntelligence(tabKey) {
  try {
    const res = await fetch('/api/admin/system-intelligence');
    const data = await res.json();
    const box = document.getElementById('intel-display-box');

    if (tabKey === 'queue') {
      let qHtml = `
        <h4 style="font-size:1.1rem; color:#ffffff; margin-bottom:0.75rem;">Queue Intelligence & Throughput Balancer</h4>
        <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:1rem;">${data.queue_intelligence.smoothing_algorithm}</p>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:0.75rem;">
      `;
      data.queue_intelligence.window_distribution.forEach((w) => {
        qHtml += `
          <div class="glass-card" style="padding:0.75rem;">
            <strong>${w.arrival_window_start} - ${w.arrival_window_end}</strong>
            <div style="font-size:1.2rem; font-weight:800; color:#60a5fa;">${w.count} Farmers</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">Allocated Volume: ${w.total_weight} Q</div>
          </div>
        `;
      });
      qHtml += '</div>';
      box.innerHTML = qHtml;
    } else if (tabKey === 'storage') {
      const st = data.storage_intelligence;
      box.innerHTML = `
        <h4 style="font-size:1.1rem; color:#ffffff; margin-bottom:0.75rem;">Storage Intelligence & Saturation Forecast</h4>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:1rem;">
          <div class="glass-card">
            <div style="font-size:0.75rem; color:var(--text-muted);">Total District Godown Capacity</div>
            <div style="font-size:1.5rem; font-weight:800; color:#ffffff;">${st.total_district_capacity_q} Q</div>
          </div>
          <div class="glass-card">
            <div style="font-size:0.75rem; color:var(--text-muted);">Current Physical Stock</div>
            <div style="font-size:1.5rem; font-weight:800; color:#fbbf24;">${st.total_district_stock_q} Q</div>
          </div>
          <div class="glass-card">
            <div style="font-size:0.75rem; color:var(--text-muted);">District-wide S_fill Utilization</div>
            <div style="font-size:1.5rem; font-weight:800; color:#34d399;">${st.district_s_fill_percentage}%</div>
          </div>
        </div>
      `;
    } else if (tabKey === 'equity') {
      const eq = data.equity_engine;
      box.innerHTML = `
        <h4 style="font-size:1.1rem; color:#ffffff; margin-bottom:0.75rem;">Social Equity Engine Audit (40% Smallholder Rule)</h4>
        <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:1rem;">${eq.rule_enforcement}</p>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
          <div class="glass-card">
            <div style="font-size:0.8rem; font-weight:700; color:#34d399;">Smallholder Farmers (≤5 Acres)</div>
            <div style="font-size:1.5rem; font-weight:800;">40% Volume Reservation Strictly Enforced</div>
          </div>
          <div class="glass-card">
            <div style="font-size:0.8rem; font-weight:700; color:#fbbf24;">50Q Daily Capping & Tranching</div>
            <div style="font-size:1.5rem; font-weight:800;">${eq.tranching_audit.tranche_bookings || 0} Auto-Tranches Generated</div>
          </div>
        </div>
      `;
    } else if (tabKey === 'quality') {
      const q = data.quality_intelligence;
      box.innerHTML = `
        <h4 style="font-size:1.1rem; color:#ffffff; margin-bottom:0.75rem;">AI Quality Inspection Analytics</h4>
        <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:1rem;">${q.classification_notice}</p>
        <div style="display:flex; gap:1rem; flex-wrap:wrap;">
          <div class="glass-card" style="flex:1; min-width:200px;">
            <div style="font-size:0.75rem; color:var(--text-muted);">Analysis Model</div>
            <div style="font-size:1rem; font-weight:700; color:#ffffff;">${q.model_type}</div>
          </div>
        </div>
      `;
    } else if (tabKey === 'offline') {
      const off = data.offline_sync_monitor;
      box.innerHTML = `
        <h4 style="font-size:1.1rem; color:#ffffff; margin-bottom:0.75rem;">Offline Synchronization Engine Monitor</h4>
        <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:1rem;">Deduplication Mode: ${off.deduplication_mode}</p>
        <div style="font-size:0.85rem; color:#34d399; font-weight:700;">✓ 100% Zero-Loss Transaction Guarantee on Reconnect</div>
      `;
    } else if (tabKey === 'logistics') {
      box.innerHTML = `
        <h4 style="font-size:1.1rem; color:#ffffff; margin-bottom:0.75rem;">Logistics & Buffer Evacuation Automation</h4>
        <p style="font-size:0.8rem; color:var(--text-muted);">Auto-trigger threshold S_fill ≥ 80% with Nearest Depot Route Calculation.</p>
      `;
    }
  } catch (err) {
    console.error('System intel error:', err);
  }
}

function setupAdminEvents() {
  document.getElementById('btn-admin-refresh').addEventListener('click', loadAdminDashboard);

  document.querySelectorAll('.intel-tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.intel-tab').forEach((b) => {
        b.classList.remove('btn-primary');
        b.classList.add('btn-secondary');
      });
      btn.classList.remove('btn-secondary');
      btn.classList.add('btn-primary');
      loadSystemIntelligence(btn.getAttribute('data-intel'));
    });
  });
}

// -----------------------------------------------------------------------------
// 7. HINDI VOICE / FEATURE-PHONE SIMULATOR LOGIC
// -----------------------------------------------------------------------------
async function pressIVRKey(key) {
  const session = state.ivrSession;

  try {
    const res = await fetch('/api/voice/interactive-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: session.sessionId,
        step: session.step,
        dtmf_key: key,
        phone: session.phone,
        farmer_name: session.name,
        crop_name: session.crop,
        land_acres: session.acres,
        center_id: session.centerId
      })
    });

    const data = await res.json();
    session.step = data.next_step;
    session.promptHindi = data.prompt_hindi;

    document.getElementById('ivr-step-badge').innerText = `STEP ${Math.min(4, data.current_step)}/4`;
    document.getElementById('ivr-prompt-text').innerText = data.prompt_hindi;

    const optBox = document.getElementById('ivr-options-list');
    if (data.options) {
      optBox.innerHTML = data.options.map(o => `<div>[${o.key}] ${o.label}</div>`).join('');
    } else if (data.completed) {
      optBox.innerHTML = `<div style="color:#34d399; font-weight:700;">✓ टोकन संख्या: ${data.token_code} स्वीकृत! एसएमएस भेजा गया।</div>`;
      showToast('IVR Booking Confirmed', `Voice token ${data.token_code} created successfully via phone simulation.`, 'safe');
      loadProcurementCenters();
    }

    // Play speech synthesis in Hindi
    playCurrentIVRPrompt();

  } catch (err) {
    console.error('IVR error:', err);
  }
}

function playCurrentIVRPrompt() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const text = state.ivrSession.promptHindi || 'नमस्ते!';
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'hi-IN';
    utter.rate = 0.95;
    window.speechSynthesis.speak(utter);
  }
}

function resetIVRSession() {
  state.ivrSession = {
    sessionId: `IVR-${Date.now()}`,
    step: 1,
    phone: '9876543210',
    name: 'रामेश कुमार',
    crop: 'Wheat',
    acres: 3.5,
    centerId: 1,
    promptHindi: 'नमस्ते! सरकारी ई-खरीद किसान सेवा में आपका स्वागत है। कृपया अपनी फसल चुनने के लिए 1 दबाएं या बोलें।'
  };
  document.getElementById('ivr-step-badge').innerText = 'STEP 1/4';
  document.getElementById('ivr-prompt-text').innerText = state.ivrSession.promptHindi;
  document.getElementById('ivr-options-list').innerHTML = `
    <div>[1] गेहूं (Wheat)</div>
    <div>[2] चना (Chana)</div>
    <div>[3] तुअर / अरहर (Tur)</div>
    <div>[4] धान (Paddy)</div>
  `;
}

// -----------------------------------------------------------------------------
// 8. JUDGE 8-MINUTE EVALUATION TOUR LOGIC
// -----------------------------------------------------------------------------
async function runJudgeTourStep(stepNumber) {
  if (stepNumber === 1) {
    // 1. Small Farmer Booking (Ramesh 3.5 Acres Wheat)
    document.getElementById('tab-farmer').click();
    document.querySelector('[data-subtarget="farmer-booking"]').click();
    document.getElementById('book-phone').value = '9876543210';
    document.getElementById('book-name').value = 'Ramesh Kumar Sharma';
    document.getElementById('book-land').value = '3.5';
    state.selectedCrop = 'Wheat';
    renderCropSelector();
    updateYieldCalculation();
    showToast('Judge Tour Step 1', 'Configured Smallholder Farmer (3.5 Acres) with 40% guaranteed quota.', 'info');

  } else if (stepNumber === 2) {
    // 2. Large Farmer 50Q Auto-Tranching (Suresh 12 Acres -> 216 Q)
    document.getElementById('tab-farmer').click();
    document.querySelector('[data-subtarget="farmer-booking"]').click();
    document.getElementById('book-phone').value = '9876543211';
    document.getElementById('book-name').value = 'Suresh Pratap Singh';
    document.getElementById('book-land').value = '12.0';
    state.selectedCrop = 'Wheat';
    renderCropSelector();
    updateYieldCalculation();
    showToast('Judge Tour Step 2', 'Large Farmer (12 Acres / 216 Q) triggers automatic 50Q daily capping into sequential tranches.', 'warning');

  } else if (stepNumber === 3) {
    // 3. Storage Warning & Evacuation Alert
    document.getElementById('tab-admin').click();
    showToast('Judge Tour Step 3', 'Bilaspur PACS (84% Storage) shows Warning state and triggers 3-truck evacuation recommendation.', 'warning');

  } else if (stepNumber === 4) {
    // 4. Storage Lockout & 15km Rerouting
    document.getElementById('tab-farmer').click();
    document.querySelector('[data-subtarget="farmer-booking"]').click();
    document.getElementById('book-land').value = '3.0';
    updateYieldCalculation();
    selectCenter(3); // Sitapur (96% critical lock)
    showToast('Judge Tour Step 4', 'Sitapur PACS (96% Critical) is locked and automatically suggests nearest Kalyanpur Depot (8.2 km).', 'danger');

  } else if (stepNumber === 5) {
    // 5. AI Moisture Pre-Screening Reject (>16.5%)
    document.getElementById('tab-farmer').click();
    document.querySelector('[data-subtarget="farmer-prescreen"]').click();
    runPreScreenSimulation('wet_grain');
    showToast('Judge Tour Step 5', 'Wet Grain Sample (>16.5% moisture) rejected with drying advisory BEFORE traveling to Mandi.', 'danger');

  } else if (stepNumber === 6) {
    // 6. True Offline Check-In & Auto-Sync
    document.getElementById('tab-guard').click();
    document.getElementById('offline-sim-toggle').checked = true;
    window.offlineStorage.setSimulatedOffline(true);
    scanTokenDemo('TK-78401');
    showToast('Judge Tour Step 6', 'Simulating offline gate check-in stored in IndexedDB. Toggle switch to reconnect and see instant sync.', 'warning');

  } else if (stepNumber === 7) {
    // 7. Clerk AI Quality & Atomic Fulfillment
    document.getElementById('tab-clerk').click();
    loadClerkQueue();
    showToast('Judge Tour Step 7', 'Clerk queue allows AI quality inspection, tolerance validation, and 1-click atomic fulfillment.', 'info');
  }
}

async function resetDemoData() {
  try {
    const res = await fetch('/api/admin/reset-demo-data', { method: 'POST' });
    if (res.ok) {
      showToast('Demo State Reset', 'Database and demo data refreshed to pristine default state.', 'safe');
      loadProcurementCenters();
      loadClerkQueue();
      loadAdminDashboard();
      resetIVRSession();
    }
  } catch (err) {
    console.error('Reset demo error:', err);
  }
}

// -----------------------------------------------------------------------------
// APP INITIALIZATION
// -----------------------------------------------------------------------------
window.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  renderCropSelector();
  setupBookingForm();
  setupGuardEvents();
  setupClerkEvents();
  setupAdminEvents();
  loadProcurementCenters();
  updateYieldCalculation();

  // Prescreen file upload listener
  const fileInput = document.getElementById('prescreen-file-input');
  if (fileInput) {
    fileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (file) {
        document.getElementById('prescreen-filename-text').innerText = file.name;
        const formData = new FormData();
        formData.append('crop_name', state.selectedCrop);
        formData.append('file', file);

        try {
          const res = await fetch('/api/farmer/pre-screening', {
            method: 'POST',
            body: formData
          });
          const result = await res.json();
          renderPreScreenResult(result);
        } catch (err) {
          console.error('Image analysis error:', err);
        }
      }
    });
  }

  // Register Service Worker for true browser offline support
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/service-worker.js').then(() => {
      console.log('Farmer Procurement Service Worker Registered.');
    }).catch((err) => {
      console.warn('SW registration skipped:', err);
    });
  }
});
