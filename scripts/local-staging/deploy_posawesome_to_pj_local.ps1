param(
  [string]$RepoPath = "C:\vs code repos\POS-Awesome-pj",
  [switch]$SkipContainerRestart
)

$ErrorActionPreference = "Stop"

$allContainers = @(
  "pj-production-backend-1",
  "pj-production-queue-short-1",
  "pj-production-queue-long-1",
  "pj-production-scheduler-1",
  "pj-production-websocket-1",
  "pj-production-frontend-1"
)

$pythonContainers = @(
  "pj-production-backend-1",
  "pj-production-queue-short-1",
  "pj-production-queue-long-1",
  "pj-production-scheduler-1",
  "pj-production-websocket-1"
)

$appPath = "/home/frappe/frappe-bench/apps/posawesome"
$nestedPkgPath = "/home/frappe/frappe-bench/apps/posawesome/posawesome"
$frontendPublicPath = "/home/frappe/frappe-bench/apps/posawesome/public"
$portlandPosOverrideShimLocal = Join-Path $env:TEMP "pj-local-portland-pos_override_shim.js"
$posawesomeSalesPersonShimLocal = Join-Path $env:TEMP "pj-local-posawesome-sales_person_commiss.js"
$posawesomeSalesPartnerShimLocal = Join-Path $env:TEMP "pj-local-posawesome-sales_partner_commis.js"
$posawesomeVuetifyJsLocal = Join-Path $env:TEMP "pj-local-posawesome-vuetify.js"
$posawesomeVuetifyCssLocal = Join-Path $env:TEMP "pj-local-posawesome-vuetify.min.css"

@'
// Local staging compatibility shim: disable raw ESM pos_override on pj.local to prevent runtime crash.
;(function(){try{window.__PJ_LOCAL_PORTLAND_POS_OVERRIDE_SHIM__=true;if(window.console&&console.warn){console.warn("local staging shim: portland_jewellers_custom pos_override disabled");}}catch(_e){}})();
'@ | Set-Content -Path $portlandPosOverrideShimLocal -Encoding ascii

@'
// Local staging compatibility shim for missing legacy POSAwesome include.
;(function(){try{window.__PJ_LOCAL_POSAWESOME_SALES_PERSON_COMMISS_SHIM__=true;}catch(_e){}})();
'@ | Set-Content -Path $posawesomeSalesPersonShimLocal -Encoding ascii

@'
// Local staging compatibility shim for missing legacy POSAwesome include.
;(function(){try{window.__PJ_LOCAL_POSAWESOME_SALES_PARTNER_COMMIS_SHIM__=true;}catch(_e){}})();
'@ | Set-Content -Path $posawesomeSalesPartnerShimLocal -Encoding ascii

$hostVuetifyJs = Join-Path $RepoPath "node_modules\\vuetify\\dist\\vuetify.js"
$hostVuetifyCss = Join-Path $RepoPath "node_modules\\vuetify\\dist\\vuetify.min.css"
if (Test-Path $hostVuetifyJs) {
  Copy-Item -Force $hostVuetifyJs $posawesomeVuetifyJsLocal
} else {
@'
// Local staging fallback shim for legacy Vuetify asset path expected by hooks.py.
;(function(){try{
  window.__PJ_LOCAL_POSAWESOME_VUETIFY_SHIM__=true;
  if (!window.Vuetify) {
    window.Vuetify = function VuetifyShim(opts){ return opts || {}; };
  }
}catch(_e){}})();
'@ | Set-Content -Path $posawesomeVuetifyJsLocal -Encoding ascii
}
if (Test-Path $hostVuetifyCss) {
  Copy-Item -Force $hostVuetifyCss $posawesomeVuetifyCssLocal
} else {
@'
/* Local staging fallback shim for missing Vuetify CSS asset. */
'@ | Set-Content -Path $posawesomeVuetifyCssLocal -Encoding ascii
}

function Invoke-Docker {
  param([string]$Command)
  & docker $Command
  if ($LASTEXITCODE -ne 0) {
    throw "Docker command failed: docker $Command"
  }
}

Write-Host "== Local staging deploy: posawesome -> pj.local ==" -ForegroundColor Cyan
Write-Host "RepoPath: $RepoPath"

if (-not (Test-Path (Join-Path $RepoPath "posawesome"))) {
  throw "Repo path does not contain 'posawesome': $RepoPath"
}

Write-Host "== Copying posawesome app into containers =="
foreach ($c in $allContainers) {
  Write-Host "[$c] replacing $appPath"
  & docker exec -u 0 $c sh -lc "rm -rf $appPath"
  if ($LASTEXITCODE -ne 0) { throw "Failed removing app in $c" }
  & docker cp (Join-Path $RepoPath "posawesome") "${c}:/home/frappe/frappe-bench/apps/"
  if ($LASTEXITCODE -ne 0) { throw "Failed copying app into $c" }
  & docker exec -u 0 $c sh -lc "chown -R frappe:frappe $appPath"
  if ($LASTEXITCODE -ne 0) { throw "Failed chown app folder in $c" }
}

Write-Host "== Applying nested hooks compatibility shim (python containers) =="
foreach ($c in $pythonContainers) {
  Write-Host "[$c] shim hooks.py + __init__.py + modules.txt into nested package"
  & docker exec -u 0 $c sh -lc "cp $appPath/hooks.py $nestedPkgPath/hooks.py && cp $appPath/__init__.py $nestedPkgPath/__init__.py && cp $appPath/modules.txt $nestedPkgPath/modules.txt && chown frappe:frappe $nestedPkgPath/hooks.py $nestedPkgPath/__init__.py $nestedPkgPath/modules.txt"
  if ($LASTEXITCODE -ne 0) { throw "Failed shim in $c" }
}

Write-Host "== Applying nested public compatibility shim (all containers) =="
foreach ($c in $allContainers) {
  Write-Host "[$c] shim nested public -> top-level public"
  & docker exec -u 0 $c sh -lc "rm -rf $nestedPkgPath/public && ln -s ../public $nestedPkgPath/public && chown -h frappe:frappe $nestedPkgPath/public"
  if ($LASTEXITCODE -ne 0) { throw "Failed nested public shim in $c" }
}

Write-Host "== Applying nested root-module compatibility shims (python containers) =="
foreach ($c in $pythonContainers) {
  Write-Host "[$c] shim posawesome.overrides/config/templates/translations/utils"
  & docker exec -u 0 $c sh -lc "rm -rf $nestedPkgPath/overrides $nestedPkgPath/config $nestedPkgPath/templates $nestedPkgPath/translations && rm -f $nestedPkgPath/utils.py $nestedPkgPath/api.py $nestedPkgPath/uninstall.py && ln -s ../overrides $nestedPkgPath/overrides && ln -s ../config $nestedPkgPath/config && ln -s ../templates $nestedPkgPath/templates && ln -s ../translations $nestedPkgPath/translations && ln -s ../utils.py $nestedPkgPath/utils.py && ln -s ../api.py $nestedPkgPath/api.py && ln -s ../uninstall.py $nestedPkgPath/uninstall.py && chown -h frappe:frappe $nestedPkgPath/overrides $nestedPkgPath/config $nestedPkgPath/templates $nestedPkgPath/translations $nestedPkgPath/utils.py $nestedPkgPath/api.py $nestedPkgPath/uninstall.py"
  if ($LASTEXITCODE -ne 0) { throw "Failed nested root-module compatibility shim in $c" }
}

Write-Host "== Fixing posawesome assets symlink (all containers) =="
foreach ($c in $allContainers) {
  Write-Host "[$c] recreate sites/assets/posawesome symlink"
  & docker exec -u 0 $c sh -lc "mkdir -p /home/frappe/frappe-bench/sites/assets && rm -rf /home/frappe/frappe-bench/sites/assets/posawesome && ln -s /home/frappe/frappe-bench/apps/posawesome/posawesome/public /home/frappe/frappe-bench/sites/assets/posawesome && chown -h frappe:frappe /home/frappe/frappe-bench/sites/assets/posawesome"
  if ($LASTEXITCODE -ne 0) { throw "Failed assets symlink fix in $c" }
}

Write-Host "== Applying nested Python package alias shim (python containers) =="
foreach ($c in $pythonContainers) {
  Write-Host "[$c] shim posawesome.posawesome.* imports"
  & docker exec -u 0 $c sh -lc "mkdir -p $nestedPkgPath/posawesome && printf 'import os`n_parent = os.path.dirname(os.path.dirname(__file__))`n__path__ = [_parent]`n' > $nestedPkgPath/posawesome/__init__.py && rm -rf $nestedPkgPath/posawesome/page $nestedPkgPath/posawesome/doctype $nestedPkgPath/posawesome/workspace $nestedPkgPath/posawesome/public $nestedPkgPath/posawesome/api $nestedPkgPath/posawesome/overrides && ln -s ../page $nestedPkgPath/posawesome/page && ln -s ../doctype $nestedPkgPath/posawesome/doctype && ln -s ../workspace $nestedPkgPath/posawesome/workspace && ln -s ../public $nestedPkgPath/posawesome/public && ln -s ../api $nestedPkgPath/posawesome/api && ln -s ../overrides $nestedPkgPath/posawesome/overrides && chown -R frappe:frappe $nestedPkgPath/posawesome"
  if ($LASTEXITCODE -ne 0) { throw "Failed nested Python alias shim in $c" }
}

Write-Host "== Building posawesome assets in backend container =="
& docker exec pj-production-backend-1 sh -lc "cd /home/frappe/frappe-bench && bench build --app posawesome"
if ($LASTEXITCODE -ne 0) { throw "bench build failed in backend container" }

Write-Host "== Applying local legacy bundle compatibility (backend) =="
& docker exec -u 0 pj-production-backend-1 sh -lc 'set -e; BUNDLE=$(ls /home/frappe/frappe-bench/apps/posawesome/posawesome/public/dist/js/posawesome.bundle.*.js | head -n 1); mkdir -p /home/frappe/frappe-bench/apps/posawesome/public/js; cp "$BUNDLE" /home/frappe/frappe-bench/apps/posawesome/public/js/posawesome.bundle.js; chown frappe:frappe /home/frappe/frappe-bench/apps/posawesome/public/js/posawesome.bundle.js'
if ($LASTEXITCODE -ne 0) { throw "Failed backend legacy bundle compatibility copy" }

Write-Host "== Applying local legacy posawesome include compatibility shims (backend) =="
& docker exec -u 0 pj-production-backend-1 sh -lc "mkdir -p /home/frappe/frappe-bench/apps/posawesome/public/js /home/frappe/frappe-bench/apps/posawesome/public/node_modules/vuetify/dist"
if ($LASTEXITCODE -ne 0) { throw "Failed backend posawesome shim dirs create" }
& docker cp $posawesomeSalesPersonShimLocal "pj-production-backend-1:/tmp/pj-local-sales_person_commiss.js"
if ($LASTEXITCODE -ne 0) { throw "Failed copying backend sales_person_commiss shim" }
& docker cp $posawesomeSalesPartnerShimLocal "pj-production-backend-1:/tmp/pj-local-sales_partner_commis.js"
if ($LASTEXITCODE -ne 0) { throw "Failed copying backend sales_partner_commis shim" }
& docker cp $posawesomeVuetifyJsLocal "pj-production-backend-1:/tmp/pj-local-vuetify.js"
if ($LASTEXITCODE -ne 0) { throw "Failed copying backend vuetify shim" }
& docker cp $posawesomeVuetifyCssLocal "pj-production-backend-1:/tmp/pj-local-vuetify.min.css"
if ($LASTEXITCODE -ne 0) { throw "Failed copying backend vuetify css shim" }
& docker exec -u 0 pj-production-backend-1 sh -lc 'cp /tmp/pj-local-sales_person_commiss.js /home/frappe/frappe-bench/apps/posawesome/public/js/sales_person_commiss.js && cp /tmp/pj-local-sales_partner_commis.js /home/frappe/frappe-bench/apps/posawesome/public/js/sales_partner_commis.js && cp /tmp/pj-local-vuetify.js /home/frappe/frappe-bench/apps/posawesome/public/node_modules/vuetify/dist/vuetify.js && cp /tmp/pj-local-vuetify.min.css /home/frappe/frappe-bench/apps/posawesome/public/node_modules/vuetify/dist/vuetify.min.css && chown frappe:frappe /home/frappe/frappe-bench/apps/posawesome/public/js/sales_person_commiss.js /home/frappe/frappe-bench/apps/posawesome/public/js/sales_partner_commis.js /home/frappe/frappe-bench/apps/posawesome/public/node_modules/vuetify/dist/vuetify.js /home/frappe/frappe-bench/apps/posawesome/public/node_modules/vuetify/dist/vuetify.min.css && rm -f /tmp/pj-local-sales_person_commiss.js /tmp/pj-local-sales_partner_commis.js /tmp/pj-local-vuetify.js /tmp/pj-local-vuetify.min.css'
if ($LASTEXITCODE -ne 0) { throw "Failed backend posawesome compatibility shim install" }

Write-Host "== Building portland_jewellers_custom assets in backend container (local parity) =="
& docker exec pj-production-backend-1 sh -lc "cd /home/frappe/frappe-bench && bench build --app portland_jewellers_custom"
if ($LASTEXITCODE -ne 0) { throw "bench build failed for portland_jewellers_custom in backend container" }

Write-Host "== Applying local legacy pos_override compatibility (backend) =="
& docker exec -u 0 pj-production-backend-1 sh -lc "mkdir -p /home/frappe/frappe-bench/apps/portland_jewellers_custom/portland_jewellers_custom/public/js"
if ($LASTEXITCODE -ne 0) { throw "Failed backend portland pos_override shim dir create" }
& docker cp $portlandPosOverrideShimLocal "pj-production-backend-1:/tmp/pj-local-portland-pos_override_shim.js"
if ($LASTEXITCODE -ne 0) { throw "Failed copying backend portland pos_override shim temp file" }
& docker exec -u 0 pj-production-backend-1 sh -lc 'OUT=/home/frappe/frappe-bench/apps/portland_jewellers_custom/portland_jewellers_custom/public/js/pos_override.js; cp /tmp/pj-local-portland-pos_override_shim.js "$OUT"; chown frappe:frappe "$OUT"; rm -f /tmp/pj-local-portland-pos_override_shim.js'
if ($LASTEXITCODE -ne 0) { throw "Failed backend portland pos_override compatibility copy" }

Write-Host "== Syncing built assets + manifest from backend to frontend container =="
$tempAssetsDir = Join-Path $env:TEMP "pj-local-assets-sync"
if (Test-Path $tempAssetsDir) { Remove-Item -Recurse -Force $tempAssetsDir }
New-Item -ItemType Directory -Path $tempAssetsDir | Out-Null

& docker cp "pj-production-backend-1:/home/frappe/frappe-bench/sites/assets/assets.json" (Join-Path $tempAssetsDir "assets.json")
if ($LASTEXITCODE -ne 0) { throw "Failed copying assets.json from backend" }
& docker cp "pj-production-backend-1:/home/frappe/frappe-bench/sites/assets/assets-rtl.json" (Join-Path $tempAssetsDir "assets-rtl.json")
if ($LASTEXITCODE -ne 0) { throw "Failed copying assets-rtl.json from backend" }
& docker cp "pj-production-backend-1:/home/frappe/frappe-bench/apps/posawesome/posawesome/public/dist" (Join-Path $tempAssetsDir "dist")
if ($LASTEXITCODE -ne 0) { throw "Failed copying posawesome dist assets from backend" }
& docker cp "pj-production-backend-1:/home/frappe/frappe-bench/apps/portland_jewellers_custom/portland_jewellers_custom/public/dist" (Join-Path $tempAssetsDir "portland-dist")
if ($LASTEXITCODE -ne 0) { throw "Failed copying portland_jewellers_custom dist assets from backend" }

& docker exec -u 0 pj-production-frontend-1 sh -lc "rm -rf /home/frappe/frappe-bench/apps/posawesome/posawesome/public/dist"
if ($LASTEXITCODE -ne 0) { throw "Failed removing frontend posawesome dist assets" }
& docker exec -u 0 pj-production-frontend-1 sh -lc "rm -rf /home/frappe/frappe-bench/apps/portland_jewellers_custom/portland_jewellers_custom/public/dist"
if ($LASTEXITCODE -ne 0) { throw "Failed removing frontend portland dist assets" }
& docker exec -u 0 pj-production-frontend-1 sh -lc "rm -rf /home/frappe/frappe-bench/apps/portland_jewellers_custom/portland_jewellers_custom/public/portland-dist"
if ($LASTEXITCODE -ne 0) { throw "Failed removing frontend portland-dist temp assets" }
& docker cp (Join-Path $tempAssetsDir "assets.json") "pj-production-frontend-1:/home/frappe/frappe-bench/sites/assets/assets.json"
if ($LASTEXITCODE -ne 0) { throw "Failed syncing frontend assets.json" }
& docker cp (Join-Path $tempAssetsDir "assets-rtl.json") "pj-production-frontend-1:/home/frappe/frappe-bench/sites/assets/assets-rtl.json"
if ($LASTEXITCODE -ne 0) { throw "Failed syncing frontend assets-rtl.json" }
& docker cp (Join-Path $tempAssetsDir "dist") "pj-production-frontend-1:/home/frappe/frappe-bench/apps/posawesome/posawesome/public/"
if ($LASTEXITCODE -ne 0) { throw "Failed syncing frontend posawesome dist assets" }
& docker cp (Join-Path $tempAssetsDir "portland-dist") "pj-production-frontend-1:/home/frappe/frappe-bench/apps/portland_jewellers_custom/portland_jewellers_custom/public/dist"
if ($LASTEXITCODE -ne 0) { throw "Failed syncing frontend portland dist assets" }
& docker exec -u 0 pj-production-frontend-1 sh -lc 'set -e; BUNDLE=$(ls /home/frappe/frappe-bench/apps/posawesome/posawesome/public/dist/js/posawesome.bundle.*.js | head -n 1); mkdir -p /home/frappe/frappe-bench/apps/posawesome/public/js; cp "$BUNDLE" /home/frappe/frappe-bench/apps/posawesome/public/js/posawesome.bundle.js; chown frappe:frappe /home/frappe/frappe-bench/apps/posawesome/public/js/posawesome.bundle.js'
if ($LASTEXITCODE -ne 0) { throw "Failed frontend legacy bundle compatibility copy" }
& docker exec -u 0 pj-production-frontend-1 sh -lc "mkdir -p /home/frappe/frappe-bench/apps/posawesome/public/js /home/frappe/frappe-bench/apps/posawesome/public/node_modules/vuetify/dist"
if ($LASTEXITCODE -ne 0) { throw "Failed frontend posawesome shim dirs create" }
& docker cp $posawesomeSalesPersonShimLocal "pj-production-frontend-1:/tmp/pj-local-sales_person_commiss.js"
if ($LASTEXITCODE -ne 0) { throw "Failed copying frontend sales_person_commiss shim" }
& docker cp $posawesomeSalesPartnerShimLocal "pj-production-frontend-1:/tmp/pj-local-sales_partner_commis.js"
if ($LASTEXITCODE -ne 0) { throw "Failed copying frontend sales_partner_commis shim" }
& docker cp $posawesomeVuetifyJsLocal "pj-production-frontend-1:/tmp/pj-local-vuetify.js"
if ($LASTEXITCODE -ne 0) { throw "Failed copying frontend vuetify shim" }
& docker cp $posawesomeVuetifyCssLocal "pj-production-frontend-1:/tmp/pj-local-vuetify.min.css"
if ($LASTEXITCODE -ne 0) { throw "Failed copying frontend vuetify css shim" }
& docker exec -u 0 pj-production-frontend-1 sh -lc 'cp /tmp/pj-local-sales_person_commiss.js /home/frappe/frappe-bench/apps/posawesome/public/js/sales_person_commiss.js && cp /tmp/pj-local-sales_partner_commis.js /home/frappe/frappe-bench/apps/posawesome/public/js/sales_partner_commis.js && cp /tmp/pj-local-vuetify.js /home/frappe/frappe-bench/apps/posawesome/public/node_modules/vuetify/dist/vuetify.js && cp /tmp/pj-local-vuetify.min.css /home/frappe/frappe-bench/apps/posawesome/public/node_modules/vuetify/dist/vuetify.min.css && chown frappe:frappe /home/frappe/frappe-bench/apps/posawesome/public/js/sales_person_commiss.js /home/frappe/frappe-bench/apps/posawesome/public/js/sales_partner_commis.js /home/frappe/frappe-bench/apps/posawesome/public/node_modules/vuetify/dist/vuetify.js /home/frappe/frappe-bench/apps/posawesome/public/node_modules/vuetify/dist/vuetify.min.css && rm -f /tmp/pj-local-sales_person_commiss.js /tmp/pj-local-sales_partner_commis.js /tmp/pj-local-vuetify.js /tmp/pj-local-vuetify.min.css'
if ($LASTEXITCODE -ne 0) { throw "Failed frontend posawesome compatibility shim install" }
& docker exec -u 0 pj-production-frontend-1 sh -lc "mkdir -p /home/frappe/frappe-bench/apps/portland_jewellers_custom/portland_jewellers_custom/public/js"
if ($LASTEXITCODE -ne 0) { throw "Failed frontend portland pos_override shim dir create" }
& docker cp $portlandPosOverrideShimLocal "pj-production-frontend-1:/tmp/pj-local-portland-pos_override_shim.js"
if ($LASTEXITCODE -ne 0) { throw "Failed copying frontend portland pos_override shim temp file" }
& docker exec -u 0 pj-production-frontend-1 sh -lc 'OUT=/home/frappe/frappe-bench/apps/portland_jewellers_custom/portland_jewellers_custom/public/js/pos_override.js; cp /tmp/pj-local-portland-pos_override_shim.js "$OUT"; chown frappe:frappe "$OUT"; rm -f /tmp/pj-local-portland-pos_override_shim.js'
if ($LASTEXITCODE -ne 0) { throw "Failed frontend portland pos_override compatibility copy" }
& docker exec -u 0 pj-production-frontend-1 sh -lc "chown -R frappe:frappe /home/frappe/frappe-bench/apps/posawesome/posawesome/public/dist /home/frappe/frappe-bench/apps/portland_jewellers_custom/portland_jewellers_custom/public/dist /home/frappe/frappe-bench/sites/assets/assets.json /home/frappe/frappe-bench/sites/assets/assets-rtl.json"
if ($LASTEXITCODE -ne 0) { throw "Failed chown frontend synced assets" }

Write-Host "== Running local site migrate (pj.local) =="
& docker exec pj-production-backend-1 sh -lc "cd /home/frappe/frappe-bench && bench --site pj.local migrate"
if ($LASTEXITCODE -ne 0) { throw "bench migrate failed" }

Write-Host "== Clearing local site cache (pj.local) =="
& docker exec pj-production-backend-1 sh -lc "cd /home/frappe/frappe-bench && bench --site pj.local clear-cache"
if ($LASTEXITCODE -ne 0) { throw "bench clear-cache failed" }

Write-Host "== Rebuilding local permissions/module cache for cline (pj.local) =="
$cacheFixPy = @'
import os
os.chdir("/home/frappe/frappe-bench/sites")
import frappe
frappe.init(site="pj.local")
frappe.connect()
try:
    user = "cline@pjjamaica.com"
    frappe.clear_cache(user=user)
    frappe.set_user(user)
    frappe.get_user().build_permissions()
    frappe.clear_cache()
    print("cache_fix_ok", user)
finally:
    frappe.destroy()
'@
$cacheFixPy | & wsl -d Ubuntu-24.04 -- docker exec -i pj-production-backend-1 bash -lc "cd /home/frappe/frappe-bench && source env/bin/activate && export PYTHONPATH=/home/frappe/frappe-bench/apps/frappe:/home/frappe/frappe-bench/apps/erpnext:/home/frappe/frappe-bench/apps/posawesome:/home/frappe/frappe-bench/apps/portland_jewellers_custom && python -"
if ($LASTEXITCODE -ne 0) { throw "Failed local cache/permissions rebuild for cline" }

if (-not $SkipContainerRestart) {
  Write-Host "== Restarting local staging app containers =="
  & docker restart @allContainers | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "docker restart failed" }
  Start-Sleep -Seconds 5
}

Write-Host "== Verifying pj.local ==" -ForegroundColor Cyan
$loginResp = Invoke-WebRequest "http://pj.local:8080/login" -UseBasicParsing -TimeoutSec 30
Write-Host "pj.local /login status: $($loginResp.StatusCode)"

Write-Host "== Local staging deploy complete ==" -ForegroundColor Green
