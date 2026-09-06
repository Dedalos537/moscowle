export function base64urlToBuffer(b64url: string): ArrayBuffer {
  const base64 = b64url.replace(/-/g, '+').replace(/_/g, '/');
  const normalized = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
  const bytes = Uint8Array.from(atob(normalized), c => c.charCodeAt(0));
  return bytes.buffer as ArrayBuffer;
}

export function bufferToBase64url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export interface SerializedCredential {
  id: string;
  rawId: string;
  type: string;
  response: Record<string, string>;
  clientExtensionResults: any;
}

export function serializeWebauthnCredential(cred: PublicKeyCredential): SerializedCredential {
  const response: Record<string, string> = {};
  const data: any = cred.response;

  const toBuffer = (value: any): ArrayBuffer | undefined => {
    if (value instanceof ArrayBuffer) return value;
    if (ArrayBuffer.isView(value)) {
      const view = value as ArrayBufferView;
      return view.buffer.slice(view.byteOffset, view.byteOffset + view.byteLength);
    }
    return undefined;
  };

  const map: Array<[string, any]> = [
    ['clientDataJSON', data.clientDataJSON],
    ['authenticatorData', data.authenticatorData],
    ['signature', data.signature],
    ['userHandle', data.userHandle],
    ['attestationObject', data.attestationObject],
  ];
  for (const [key, value] of map) {
    const enc = toBuffer(value);
    if (enc !== undefined) {
      response[key] = bufferToBase64url(enc);
    }
  }

  return {
    id: cred.id,
    rawId: bufferToBase64url(cred.rawId),
    type: cred.type,
    response,
    clientExtensionResults: cred.getClientExtensionResults ? cred.getClientExtensionResults() : {},
  };
}
