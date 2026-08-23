import { scryptSync, randomBytes, createCipheriv } from "node:crypto";
import Database from "better-sqlite3";

const PREFIX = "enc:v1:";
const ALGORITHM = "aes-256-gcm";
const IV_LENGTH = 16;
const KEY_LENGTH = 32;
const AUTH_TAG_LENGTH = 16;
const STATIC_SALT = "omniroute-field-encryption-v1";

const secret = "106d589ac39bf22b37bfb1ea268e74336ef0c083985bcb1f461f7ee2409285a1";
const plaintext = "sk-gVAD1EdViBQivX5aMx3Y32Jn2Yja3R6ooIN08jIDxTFVErZd4r0SDlq9Ud5R6wcu";

const key = scryptSync(secret, STATIC_SALT, KEY_LENGTH);
const iv = randomBytes(IV_LENGTH);
const cipher = createCipheriv(ALGORITHM, key, iv);
let encrypted = cipher.update(plaintext, "utf8", "hex");
encrypted += cipher.final("hex");
const authTag = cipher.getAuthTag().toString("hex");
const encBlob = `${PREFIX}${iv.toString("hex")}:${encrypted}:${authTag}`;

const db = new Database("C:\\Users\\Motunrayo\\.omniroute\\storage.sqlite");
const result = db.prepare(
  "UPDATE provider_connections SET api_key=?, test_status=NULL, last_error=NULL, error_code=NULL WHERE provider='opencode'"
).run(encBlob);

console.log("rows_updated:", result.changes);

// verify
const row = db.prepare("SELECT id, provider, api_key IS NOT NULL AS has_key, test_status FROM provider_connections WHERE provider='opencode'").get();
console.log("verify:", row);
db.close();