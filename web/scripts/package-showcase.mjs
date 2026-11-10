import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = process.argv[2] && path.resolve(process.argv[2]);
if (!output || fs.existsSync(output)) throw new Error("Provide a new output directory; existing packages are never overwritten.");
const assets = ["index.html","styles.css","theme.js","app.js","api.js","config.js",
  "paper-chat.js","paper-api.js","paper-reader.js","favicon.svg","apple-touch-icon.png",
  "og-image.png","robots.txt","sitemap.xml","mock/papers.json"];
fs.mkdirSync(output,{recursive:true});
for (const name of assets) {
  const target = path.join(output,name);
  fs.mkdirSync(path.dirname(target),{recursive:true});
  fs.copyFileSync(path.join(root,name),target);
}
const config = path.join(output,"config.js");
const text = fs.readFileSync(config,"utf8");
let showcase = text;
for (const [field, value] of Object.entries({
  SHOWCASE_ONLY: true, PAPER_API_ENABLED: false, PAPER_PREPARE_ONLY: false,
})) {
  const pattern = new RegExp(`\\b${field}: (?:true|false)\\b`, "g");
  if ([...showcase.matchAll(pattern)].length !== 1) throw new Error(`Expected one boolean ${field} configuration.`);
  showcase = showcase.replace(pattern, `${field}: ${value}`);
}
fs.writeFileSync(config,showcase);
const settings = JSON.parse(fs.readFileSync(path.join(root,"vercel.json"),"utf8"));
delete settings.ignoreCommand;
settings.framework = null;
settings.buildCommand = "";
fs.writeFileSync(path.join(output,"vercel.json"),JSON.stringify(settings,null,2)+"\n");
console.log(JSON.stringify({output,files:assets.length+1,showcase:true,backend:false,model_calls:false}));
