export function workflowStatusColor(status) {
  var s = (status || '').toString();
  if (s === 'Unpaid') return 'orange';
  if (s === 'Paid') return 'blue';
  if (s === 'Picking') return 'deep-purple';
  if (s === 'Picked') return 'green';
  if (s === 'On Hold') return 'red darken-1';
  if (s === 'Dispatched') return 'teal';
  return 'grey';
}

export function normalizeWorkflowStatus(value) {
  return String(value || '').trim().toLowerCase();
}

export function workflowCurrentLabel(row) {
  var displayStatus = String((row && row.display_status) || '').trim();
  var tokenStatus = normalizeWorkflowStatus(row && row.token_status);
  var pickingStatus = normalizeWorkflowStatus(row && row.picking_status);
  var dispatchStatus = normalizeWorkflowStatus(row && row.dispatch_status);

  if (displayStatus === 'Dispatched' || dispatchStatus === 'released') {
    return __('Current state: Dispatched / released');
  }
  if (displayStatus === 'On Hold' || dispatchStatus === 'on hold' || pickingStatus === 'exception') {
    return __('Current state: On hold / exception');
  }
  if (displayStatus === 'Picked' || pickingStatus === 'picked') {
    return __('Current state: Picked, ready for dispatch');
  }
  if (displayStatus === 'Picking' || pickingStatus === 'in progress') {
    return __('Current state: Picking in progress');
  }
  if (displayStatus === 'Paid' || tokenStatus === 'paid') {
    return __('Current state: Paid, waiting for picking');
  }
  if (tokenStatus === 'expired') {
    return __('Current state: Token expired');
  }
  if (tokenStatus === 'abandoned') {
    return __('Current state: Token abandoned');
  }
  return __('Current state: Token created, payment pending');
}

export function workflowSteps(row) {
  var tokenStatus = normalizeWorkflowStatus(row && row.token_status);
  var pickingStatus = normalizeWorkflowStatus(row && row.picking_status);
  var dispatchStatus = normalizeWorkflowStatus(row && row.dispatch_status);
  var isPaid = tokenStatus === 'paid';
  var isPicking = pickingStatus === 'in progress';
  var isPicked = pickingStatus === 'picked';
  var isException = pickingStatus === 'exception' || dispatchStatus === 'on hold';
  var isReleased = dispatchStatus === 'released';
  var isTerminalToken = tokenStatus === 'expired' || tokenStatus === 'abandoned';

  var paymentState = 'pending';
  if (isPaid || isPicked || isReleased || isPicking || isException) {
    paymentState = 'done';
  } else if (isTerminalToken) {
    paymentState = 'blocked';
  } else {
    paymentState = 'active';
  }

  var pickState = 'pending';
  if (isPicked || isReleased) {
    pickState = 'done';
  } else if (isException) {
    pickState = 'blocked';
  } else if (isPicking || isPaid) {
    pickState = 'active';
  }

  var dispatchState = 'pending';
  if (isReleased) {
    dispatchState = 'done';
  } else if (isException) {
    dispatchState = 'blocked';
  } else if (isPicked) {
    dispatchState = 'active';
  }

  return [
    {
      key: 'token',
      label: __('Token'),
      icon: 'mdi-ticket-confirmation-outline',
      state: isTerminalToken ? 'blocked' : 'done',
    },
    {
      key: 'payment',
      label: __('Payment'),
      icon: 'mdi-cash-register',
      state: paymentState,
    },
    {
      key: 'pick',
      label: __('Pick'),
      icon: 'mdi-package-variant-closed',
      state: pickState,
    },
    {
      key: 'dispatch',
      label: __('Dispatch'),
      icon: 'mdi-truck-check-outline',
      state: dispatchState,
    },
  ];
}

export function workflowStateAria(row) {
  return [
    workflowCurrentLabel(row),
    __('Token') + ': ' + ((row && row.token_status) || '-'),
    __('Pick') + ': ' + ((row && row.picking_status) || '-'),
    __('Dispatch') + ': ' + ((row && row.dispatch_status) || '-'),
  ].join(', ');
}
