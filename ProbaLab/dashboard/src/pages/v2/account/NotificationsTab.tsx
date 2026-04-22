import { useState } from 'react';
import { ChannelsCard } from '@/components/v2/account/notifications/ChannelsCard';
import { RulesList } from '@/components/v2/account/notifications/RulesList';
import { RuleBuilderModal } from '@/components/v2/account/notifications/RuleBuilderModal';
import { DeleteRuleConfirm } from '@/components/v2/account/notifications/DeleteRuleConfirm';
import type { NotificationRule } from '@/lib/v2/schemas/rules';

export interface NotificationsTabProps {
  'data-testid'?: string;
}

/**
 * "Notifications" tab for the account area.
 *
 * Composes the channels card (Telegram / Email / Push) with the rules
 * list. The tab owns the modal lifecycle : opening a rule for edit,
 * opening a brand new rule or opening the destructive delete
 * confirmation. Child components only declare what they want to do
 * and leave the modal orchestration here.
 */
export function NotificationsTab({
  'data-testid': dataTestId = 'notifications-tab',
}: NotificationsTabProps = {}) {
  const [isCreating, setIsCreating] = useState(false);
  const [editingRule, setEditingRule] = useState<NotificationRule | null>(null);
  const [deletingRule, setDeletingRule] = useState<NotificationRule | null>(
    null,
  );

  return (
    <section
      data-testid={dataTestId}
      aria-label="Notifications"
      className="space-y-8"
    >
      <header>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Notifications
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Choisis où ProbaLab t’envoie ses alertes et quand elles se
          déclenchent.
        </p>
      </header>

      <ChannelsCard />

      <RulesList
        onCreate={() => setIsCreating(true)}
        onEdit={(rule) => setEditingRule(rule)}
        onDeleteRequest={(rule) => setDeletingRule(rule)}
      />

      <RuleBuilderModal
        open={isCreating}
        onOpenChange={(open) => setIsCreating(open)}
      />

      <RuleBuilderModal
        key={editingRule?.id ?? 'no-edit'}
        open={editingRule !== null}
        onOpenChange={(open) => {
          if (!open) setEditingRule(null);
        }}
        initialRule={editingRule ?? undefined}
      />

      <DeleteRuleConfirm
        rule={deletingRule}
        onOpenChange={(open) => {
          if (!open) setDeletingRule(null);
        }}
      />
    </section>
  );
}

export default NotificationsTab;
