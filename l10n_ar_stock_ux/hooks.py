import logging

from odoo.modules.module import get_manifest
from odoo.tools.convert import convert_file

_logger = logging.getLogger(__name__)

# ir.model / ir.model.fields xmlids stay on l10n_ar_stock. Official data
# references model_stock_picking, and the ORM recreates field xmlids itself.
_KEEP_MODELS = ("ir.model", "ir.model.fields", "ir.model.fields.selection")


def pre_init_hook(env):
    """Load Odoo's l10n_ar_stock views on databases migrated from ADHOC <= 18.

    Until 18.0 the technical name ``l10n_ar_stock`` was this localization. On 19
    that name is Odoo's module, which is left installed and is not upgraded when
    this module is installed. Its view
    ``stock_picking_form_inherit_l10n_ar_stock`` is therefore missing and the
    install dies in ``views/stock_picking_views.xml``.

    External ids that ADHOC already created under ``l10n_ar_stock`` are moved
    here first, so official data can create ``report_delivery_document`` and
    this module updates the old remito views instead of duplicating them.
    """
    if env.ref(
        "l10n_ar_stock.stock_picking_form_inherit_l10n_ar_stock",
        raise_if_not_found=False,
    ):
        return

    cr = env.cr
    cr.execute(
        """
        UPDATE ir_model_data AS src
           SET module = 'l10n_ar_stock_ux'
         WHERE src.module = 'l10n_ar_stock'
           AND src.model NOT IN %s
           AND NOT EXISTS (
                SELECT 1
                  FROM ir_model_data AS dst
                 WHERE dst.module = 'l10n_ar_stock_ux'
                   AND dst.name = src.name
           )
        """,
        [_KEEP_MODELS],
    )
    moved = cr.rowcount
    if moved:
        env.registry.clear_cache()
        env["ir.model.data"].invalidate_model()
        _logger.info(
            "Reassigned %s ir.model.data rows from l10n_ar_stock to l10n_ar_stock_ux",
            moved,
        )

    manifest = get_manifest("l10n_ar_stock")
    data_files = manifest["data"] if manifest else ()
    if not data_files:
        raise RuntimeError(
            "l10n_ar_stock is installed but its picking view is missing and the "
            "official module data could not be found on the addons path."
        )
    for filename in data_files:
        convert_file(env, "l10n_ar_stock", filename, {}, mode="init", noupdate=False)
    env.registry.clear_cache()
    _logger.info(
        "Loaded %s official l10n_ar_stock data files missing after the 17/18 migration",
        len(data_files),
    )
