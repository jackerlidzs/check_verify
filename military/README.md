# ChatGPT Military SheerID Verification Guide

## 📋 Overview

The ChatGPT military verification flow differs from regular student/teacher verification. It requires calling an additional endpoint to collect military status before submitting the personal information form.

## 🔄 Verification Flow

### Step 1: Collect Military Status (collectMilitaryStatus)

Before submitting the personal info form, you must first call this endpoint to set the military status.

**Request Info**:
- **URL**: `https://services.sheerid.com/rest/v2/verification/{verificationId}/step/collectMilitaryStatus`
- **Method**: `POST`
- **Body**:
```json
{
    "status": "VETERAN"
}
```

**Response Example**:
```json
{
    "verificationId": "{verification_id}",
    "currentStep": "collectInactiveMilitaryPersonalInfo",
    "errorIds": [],
    "segment": "military",
    "subSegment": "veteran",
    "locale": "en-US",
    "country": null,
    "created": 1766539517800,
    "updated": 1766540141435,
    "submissionUrl": "https://services.sheerid.com/rest/v2/verification/{verification_id}/step/collectInactiveMilitaryPersonalInfo",
    "instantMatchAttempts": 0
}
```

**Key Fields**:
- `submissionUrl`: The URL to use for the next step
- `currentStep`: Should change to `collectInactiveMilitaryPersonalInfo`

---

### Step 2: Collect Inactive Military Personal Info (collectInactiveMilitaryPersonalInfo)

Use the `submissionUrl` from Step 1 to submit personal information.

**Request Info**:
- **URL**: From Step 1 response `submissionUrl`
  - Example: `https://services.sheerid.com/rest/v2/verification/{verificationId}/step/collectInactiveMilitaryPersonalInfo`
- **Method**: `POST`
- **Body**:
```json
{
    "firstName": "name",
    "lastName": "name",
    "birthDate": "1939-12-01",
    "email": "your mail",
    "phoneNumber": "",
    "organization": {
        "id": 4070,
        "name": "Army"
    },
    "dischargeDate": "2025-05-29",
    "locale": "en-US",
    "country": "US",
    "metadata": {
        "marketConsentValue": false,
        "refererUrl": "",
        "verificationId": "",
        "flags": "{\"doc-upload-considerations\":\"default\",\"doc-upload-may24\":\"default\",\"doc-upload-redesign-use-legacy-message-keys\":false,\"docUpload-assertion-checklist\":\"default\",\"include-cvec-field-france-student\":\"not-labeled-optional\",\"org-search-overlay\":\"default\",\"org-selected-display\":\"default\"}",
        "submissionOptIn": "By submitting the personal information above, I acknowledge that my personal information is being collected under the <a target=\"_blank\" rel=\"noopener noreferrer\" class=\"sid-privacy-policy sid-link\" href=\"https://openai.com/policies/privacy-policy/\">privacy policy</a> of the business from which I am seeking a discount, and I understand that my personal information will be shared with SheerID as a processor/third-party service provider in order for SheerID to confirm my eligibility for a special offer. Contact OpenAI Support for further assistance at support@openai.com"
    }
}
```

**Field Descriptions**:
- `firstName`: First name
- `lastName`: Last name
- `birthDate`: Date of birth, format `YYYY-MM-DD`
- `email`: Email address
- `phoneNumber`: Phone number (can be empty)
- `organization`: Military organization info (see organization list below)
- `dischargeDate`: Discharge date, format `YYYY-MM-DD`
- `locale`: Locale, default `en-US`
- `country`: Country code, default `US`
- `metadata`: Metadata (includes privacy policy consent text, etc.)

---

## 🎖️ Military Organizations

Available military organization options:

| ID | Name | Description |
|----|------|-------------|
| 4070 | Army | U.S. Army |
| 4073 | Air Force | U.S. Air Force |
| 4072 | Navy | U.S. Navy |
| 4071 | Marine Corps | U.S. Marine Corps |
| 4074 | Coast Guard | U.S. Coast Guard |
| 4544268 | Space Force | U.S. Space Force |

---

## 🔑 Implementation Notes

1. **Order matters**: You MUST call `collectMilitaryStatus` first, then use the returned `submissionUrl` to call `collectInactiveMilitaryPersonalInfo`
2. **Organization info**: The `organization` field requires both `id` and `name`
3. **Date format**: `birthDate` and `dischargeDate` must use `YYYY-MM-DD` format
4. **Metadata**: The `submissionOptIn` field in metadata contains the privacy policy consent text

---

## ✅ Implementation Status

- [x] Implement `collectMilitaryStatus` API call
- [x] Implement `collectInactiveMilitaryPersonalInfo` API call
- [x] Add military organization selection logic
- [x] Generate personal info (name, birth date, email, etc.)
- [x] Generate discharge date (2025, random month 1-11)
- [x] Handle metadata (flags and submissionOptIn)
- [x] Integrate into bot command system (`/verify6`)
