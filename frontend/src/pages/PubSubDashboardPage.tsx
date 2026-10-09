import { FormEvent, useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useProject } from '../contexts/ProjectContext';
import {
  listTopics,
  createTopic,
  deleteTopic,
  listSubscriptions,
  createSubscription,
  deleteSubscription,
  publishMessage,
  pullMessages,
  acknowledgeMessages,
  nackMessages,
  Topic,
  Subscription,
  PullResponseMessage,
} from '../api/pubsub';
import { Loader2, Plus, RefreshCw, Trash2, Send, Inbox, MessageSquare } from 'lucide-react';
import { Modal, ModalButton, ModalFooter } from '../components/Modal';

type ActiveTab = 'topics' | 'subscriptions';

export default function PubSubDashboardPage() {
  const { currentProject } = useProject();
  const [activeTab, setActiveTab] = useState<ActiveTab>('topics');

  // Topics state
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topicsLoading, setTopicsLoading] = useState(true);
  const [deletingTopic, setDeletingTopic] = useState<string | null>(null);

  // Subscriptions state
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [subscriptionsLoading, setSubscriptionsLoading] = useState(true);
  const [deletingSubscription, setDeletingSubscription] = useState<string | null>(null);

  // Modals
  const [showCreateTopic, setShowCreateTopic] = useState(false);
  const [showCreateSubscription, setShowCreateSubscription] = useState(false);
  const [showPublish, setShowPublish] = useState(false);
  const [showPull, setShowPull] = useState(false);

  // Create Topic form
  const [newTopicId, setNewTopicId] = useState('');
  const [topicLabels, setTopicLabels] = useState('');
  const [creatingTopic, setCreatingTopic] = useState(false);

  // Create Subscription form
  const [newSubscriptionId, setNewSubscriptionId] = useState('');
  const [selectedTopic, setSelectedTopic] = useState('');
  const [deliveryType, setDeliveryType] = useState<'PULL' | 'PUSH'>('PULL');
  const [ackDeadline, setAckDeadline] = useState(60);
  const [subscriptionLabels, setSubscriptionLabels] = useState('');
  const [creatingSubscription, setCreatingSubscription] = useState(false);

  // Publish Message form
  const [publishTopic, setPublishTopic] = useState('');
  const [messageData, setMessageData] = useState('');
  const [messageAttributes, setMessageAttributes] = useState('');
  const [publishing, setPublishing] = useState(false);

  // Pull Messages
  const [pullSubscription, setPullSubscription] = useState('');
  const [pulledMessages, setPulledMessages] = useState<PullResponseMessage[]>([]);
  const [pulling, setPulling] = useState(false);
  const [processingAcks, setProcessingAcks] = useState<string[]>([]);

  const loadTopics = useCallback(async () => {
    try {
      setTopicsLoading(true);
      const data = await listTopics(currentProject);
      setTopics(data);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to load topics');
    } finally {
      setTopicsLoading(false);
    }
  }, [currentProject]);

  const loadSubscriptions = useCallback(async () => {
    try {
      setSubscriptionsLoading(true);
      const data = await listSubscriptions(undefined, currentProject);
      setSubscriptions(data);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to load subscriptions');
    } finally {
      setSubscriptionsLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    loadTopics();
    loadSubscriptions();
  }, [loadTopics, loadSubscriptions]);

  const parseLabels = (labelsStr: string): Record<string, string> => {
    if (!labelsStr.trim()) return {};
    try {
      const pairs = labelsStr.split(',').map((p) => p.trim());
      const labels: Record<string, string> = {};
      pairs.forEach((pair) => {
        const [key, value] = pair.split('=').map((s) => s.trim());
        if (key && value) labels[key] = value;
      });
      return labels;
    } catch {
      return {};
    }
  };

  const handleCreateTopic = async (e: FormEvent) => {
    e.preventDefault();
    const trimmedId = newTopicId.trim();
    if (!trimmedId) {
      toast.error('Topic ID is required');
      return;
    }

    setCreatingTopic(true);
    try {
      const labels = parseLabels(topicLabels);
      await createTopic(trimmedId, labels);
      toast.success(`Topic "${trimmedId}" created`);
      setShowCreateTopic(false);
      setNewTopicId('');
      setTopicLabels('');
      await loadTopics();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to create topic');
    } finally {
      setCreatingTopic(false);
    }
  };

  const handleDeleteTopic = async (topic: Topic) => {
    if (!confirm(`Delete topic "${topic.name}"?`)) return;
    setDeletingTopic(topic.name);
    try {
      await deleteTopic(topic.name);
      toast.success('Topic deleted');
      await loadTopics();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete topic');
    } finally {
      setDeletingTopic(null);
    }
  };

  const handleCreateSubscription = async (e: FormEvent) => {
    e.preventDefault();
    const trimmedId = newSubscriptionId.trim();
    if (!trimmedId) {
      toast.error('Subscription ID is required');
      return;
    }
    if (!selectedTopic) {
      toast.error('Please select a topic');
      return;
    }

    setCreatingSubscription(true);
    try {
      const labels = parseLabels(subscriptionLabels);
      await createSubscription({
        subscriptionId: trimmedId,
        topic: selectedTopic,
        labels,
        deliveryType,
        ackDeadlineSeconds: ackDeadline,
      });
      toast.success(`Subscription "${trimmedId}" created`);
      setShowCreateSubscription(false);
      setNewSubscriptionId('');
      setSelectedTopic('');
      setDeliveryType('PULL');
      setAckDeadline(60);
      setSubscriptionLabels('');
      await loadSubscriptions();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to create subscription');
    } finally {
      setCreatingSubscription(false);
    }
  };

  const handleDeleteSubscription = async (subscription: Subscription) => {
    if (!confirm(`Delete subscription "${subscription.name}"?`)) return;
    setDeletingSubscription(subscription.name);
    try {
      await deleteSubscription(subscription.name);
      toast.success('Subscription deleted');
      await loadSubscriptions();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete subscription');
    } finally {
      setDeletingSubscription(null);
    }
  };

  const handlePublishMessage = async (e: FormEvent) => {
    e.preventDefault();
    if (!publishTopic) {
      toast.error('Please select a topic');
      return;
    }
    if (!messageData.trim()) {
      toast.error('Message data is required');
      return;
    }

    setPublishing(true);
    try {
      const attributes = parseLabels(messageAttributes);
      const messageIds = await publishMessage(publishTopic, [
        { data: messageData, attributes },
      ]);
      toast.success(`Message published with ID: ${messageIds[0]}`);
      setShowPublish(false);
      setPublishTopic('');
      setMessageData('');
      setMessageAttributes('');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to publish message');
    } finally {
      setPublishing(false);
    }
  };

  const handlePullMessages = async () => {
    if (!pullSubscription) {
      toast.error('Please select a subscription');
      return;
    }

    setPulling(true);
    try {
      const messages = await pullMessages(pullSubscription, 10, true);
      setPulledMessages(messages);
      if (messages.length === 0) {
        toast('No messages available');
      } else {
        toast.success(`Pulled ${messages.length} message(s)`);
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to pull messages');
    } finally {
      setPulling(false);
    }
  };

  const handleAcknowledge = async (ackId: string) => {
    setProcessingAcks((prev) => [...prev, ackId]);
    try {
      await acknowledgeMessages(pullSubscription, [ackId]);
      toast.success('Message acknowledged');
      setPulledMessages((prev) => prev.filter((msg) => msg.ackId !== ackId));
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to acknowledge');
    } finally {
      setProcessingAcks((prev) => prev.filter((id) => id !== ackId));
    }
  };

  const handleNack = async (ackId: string) => {
    setProcessingAcks((prev) => [...prev, ackId]);
    try {
      await nackMessages(pullSubscription, [ackId]);
      toast.success('Message nacked');
      setPulledMessages((prev) => prev.filter((msg) => msg.ackId !== ackId));
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to nack');
    } finally {
      setProcessingAcks((prev) => prev.filter((id) => id !== ackId));
    }
  };

  const decodeBase64 = (data: string): string => {
    try {
      return atob(data);
    } catch {
      return data;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Pub/Sub</h1>
            <p className="text-sm text-gray-500 mt-0.5">{currentProject}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                loadTopics();
                loadSubscriptions();
              }}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
            <button
              onClick={() => setShowPublish(true)}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              <Send className="h-4 w-4" />
              Publish
            </button>
            <button
              onClick={() => setShowPull(true)}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              <Inbox className="h-4 w-4" />
              Pull
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 px-6">
        <div className="flex gap-6">
          <button
            onClick={() => setActiveTab('topics')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'topics'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <MessageSquare className="inline h-4 w-4 mr-1.5" />
            Topics ({topics.length})
          </button>
          <button
            onClick={() => setActiveTab('subscriptions')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'subscriptions'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Inbox className="inline h-4 w-4 mr-1.5" />
            Subscriptions ({subscriptions.length})
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-6 space-y-6">
        {/* Topics Tab */}
        {activeTab === 'topics' && (
          <>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Topics</h2>
              <button
                onClick={() => setShowCreateTopic(true)}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                Create Topic
              </button>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              {topicsLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                </div>
              ) : topics.length === 0 ? (
                <div className="text-center py-16">
                  <MessageSquare className="h-12 w-12 mx-auto text-gray-400 mb-3" />
                  <p className="text-gray-600 font-medium">No topics found</p>
                  <p className="text-gray-400 text-sm mt-1">Create your first topic to get started.</p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50 text-left">
                      <th className="px-4 py-3 font-medium text-gray-600">Topic ID</th>
                      <th className="px-4 py-3 font-medium text-gray-600">Labels</th>
                      <th className="px-4 py-3 font-medium text-gray-600 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {topics.map((topic) => {
                      const topicId = topic.name.split('/').pop() || topic.name;
                      return (
                        <tr key={topic.name} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900">{topicId}</td>
                          <td className="px-4 py-3 text-gray-600">
                            {topic.labels && Object.keys(topic.labels).length > 0
                              ? Object.entries(topic.labels)
                                  .map(([k, v]) => `${k}=${v}`)
                                  .join(', ')
                              : '-'}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => handleDeleteTopic(topic)}
                              disabled={deletingTopic === topic.name}
                              className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-red-600 disabled:opacity-50"
                            >
                              {deletingTopic === topic.name ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Trash2 className="h-4 w-4" />
                              )}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}

        {/* Subscriptions Tab */}
        {activeTab === 'subscriptions' && (
          <>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Subscriptions</h2>
              <button
                onClick={() => setShowCreateSubscription(true)}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                Create Subscription
              </button>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              {subscriptionsLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                </div>
              ) : subscriptions.length === 0 ? (
                <div className="text-center py-16">
                  <Inbox className="h-12 w-12 mx-auto text-gray-400 mb-3" />
                  <p className="text-gray-600 font-medium">No subscriptions found</p>
                  <p className="text-gray-400 text-sm mt-1">
                    Create a subscription to receive messages from a topic.
                  </p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50 text-left">
                      <th className="px-4 py-3 font-medium text-gray-600">Subscription ID</th>
                      <th className="px-4 py-3 font-medium text-gray-600">Topic</th>
                      <th className="px-4 py-3 font-medium text-gray-600">Delivery Type</th>
                      <th className="px-4 py-3 font-medium text-gray-600">Ack Deadline</th>
                      <th className="px-4 py-3 font-medium text-gray-600 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {subscriptions.map((sub) => {
                      const subId = sub.name.split('/').pop() || sub.name;
                      const topicId = sub.topic.split('/').pop() || sub.topic;
                      return (
                        <tr key={sub.name} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900">{subId}</td>
                          <td className="px-4 py-3 text-gray-600">{topicId}</td>
                          <td className="px-4 py-3">
                            <span
                              className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                sub.deliveryType === 'PULL'
                                  ? 'bg-blue-100 text-blue-700'
                                  : 'bg-green-100 text-green-700'
                              }`}
                            >
                              {sub.deliveryType}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-600">{sub.ackDeadlineSeconds}s</td>
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => handleDeleteSubscription(sub)}
                              disabled={deletingSubscription === sub.name}
                              className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-red-600 disabled:opacity-50"
                            >
                              {deletingSubscription === sub.name ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Trash2 className="h-4 w-4" />
                              )}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>

      {/* Create Topic Modal */}
      <Modal
        isOpen={showCreateTopic}
        onClose={() => setShowCreateTopic(false)}
        title="Create Topic"
        description="Create a new Pub/Sub topic"
      >
        <form onSubmit={handleCreateTopic}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Topic ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={newTopicId}
                onChange={(e) => setNewTopicId(e.target.value)}
                placeholder="my-topic"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Labels (optional)</label>
              <input
                type="text"
                value={topicLabels}
                onChange={(e) => setTopicLabels(e.target.value)}
                placeholder="env=prod, team=backend"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">Comma-separated key=value pairs</p>
            </div>
          </div>

          <ModalFooter>
            <ModalButton variant="secondary" onClick={() => setShowCreateTopic(false)}>
              Cancel
            </ModalButton>
            <ModalButton type="submit" disabled={creatingTopic}>
              {creatingTopic && <Loader2 className="h-4 w-4 animate-spin" />}
              Create
            </ModalButton>
          </ModalFooter>
        </form>
      </Modal>

      {/* Create Subscription Modal */}
      <Modal
        isOpen={showCreateSubscription}
        onClose={() => setShowCreateSubscription(false)}
        title="Create Subscription"
        description="Subscribe to a topic"
        size="lg"
      >
        <form onSubmit={handleCreateSubscription}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Subscription ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={newSubscriptionId}
                onChange={(e) => setNewSubscriptionId(e.target.value)}
                placeholder="my-subscription"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Topic <span className="text-red-500">*</span>
              </label>
              <select
                value={selectedTopic}
                onChange={(e) => setSelectedTopic(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              >
                <option value="">Select a topic</option>
                {topics.map((topic) => (
                  <option key={topic.name} value={topic.name}>
                    {topic.name.split('/').pop()}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Delivery Type</label>
                <select
                  value={deliveryType}
                  onChange={(e) => setDeliveryType(e.target.value as 'PULL' | 'PUSH')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="PULL">PULL</option>
                  <option value="PUSH">PUSH</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ack Deadline (seconds)
                </label>
                <input
                  type="number"
                  value={ackDeadline}
                  onChange={(e) => setAckDeadline(Number(e.target.value))}
                  min="10"
                  max="600"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Labels (optional)</label>
              <input
                type="text"
                value={subscriptionLabels}
                onChange={(e) => setSubscriptionLabels(e.target.value)}
                placeholder="env=prod, team=backend"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <ModalFooter>
            <ModalButton variant="secondary" onClick={() => setShowCreateSubscription(false)}>
              Cancel
            </ModalButton>
            <ModalButton type="submit" disabled={creatingSubscription}>
              {creatingSubscription && <Loader2 className="h-4 w-4 animate-spin" />}
              Create
            </ModalButton>
          </ModalFooter>
        </form>
      </Modal>

      {/* Publish Message Modal */}
      <Modal
        isOpen={showPublish}
        onClose={() => setShowPublish(false)}
        title="Publish Message"
        description="Publish a message to a topic"
        size="lg"
      >
        <form onSubmit={handlePublishMessage}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Topic <span className="text-red-500">*</span>
              </label>
              <select
                value={publishTopic}
                onChange={(e) => setPublishTopic(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                required
              >
                <option value="">Select a topic</option>
                {topics.map((topic) => (
                  <option key={topic.name} value={topic.name}>
                    {topic.name.split('/').pop()}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Message Data <span className="text-red-500">*</span>
              </label>
              <textarea
                value={messageData}
                onChange={(e) => setMessageData(e.target.value)}
                placeholder="Enter message content"
                rows={4}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Attributes (optional)
              </label>
              <input
                type="text"
                value={messageAttributes}
                onChange={(e) => setMessageAttributes(e.target.value)}
                placeholder="key1=value1, key2=value2"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <ModalFooter>
            <ModalButton variant="secondary" onClick={() => setShowPublish(false)}>
              Cancel
            </ModalButton>
            <ModalButton type="submit" disabled={publishing}>
              {publishing && <Loader2 className="h-4 w-4 animate-spin" />}
              Publish
            </ModalButton>
          </ModalFooter>
        </form>
      </Modal>

      {/* Pull Messages Modal */}
      <Modal
        isOpen={showPull}
        onClose={() => {
          setShowPull(false);
          setPulledMessages([]);
        }}
        title="Pull Messages"
        description="Pull messages from a subscription"
        size="xl"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Subscription</label>
            <div className="flex gap-2">
              <select
                value={pullSubscription}
                onChange={(e) => setPullSubscription(e.target.value)}
                className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">Select a subscription</option>
                {subscriptions.map((sub) => (
                  <option key={sub.name} value={sub.name}>
                    {sub.name.split('/').pop()}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={handlePullMessages}
                disabled={!pullSubscription || pulling}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {pulling ? <Loader2 className="h-4 w-4 animate-spin" /> : <Inbox className="h-4 w-4" />}
                Pull
              </button>
            </div>
          </div>

          {pulledMessages.length > 0 && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="max-h-96 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-gray-600">Message Data</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-600">Attributes</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {pulledMessages.map((msg) => (
                      <tr key={msg.ackId} className="hover:bg-gray-50">
                        <td className="px-3 py-2">
                          <pre className="text-xs font-mono whitespace-pre-wrap">
                            {decodeBase64(msg.message.data)}
                          </pre>
                        </td>
                        <td className="px-3 py-2 text-xs text-gray-600">
                          {msg.message.attributes && Object.keys(msg.message.attributes).length > 0
                            ? Object.entries(msg.message.attributes)
                                .map(([k, v]) => `${k}=${v}`)
                                .join(', ')
                            : '-'}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => handleAcknowledge(msg.ackId)}
                              disabled={processingAcks.includes(msg.ackId)}
                              className="px-2 py-1 text-xs rounded bg-green-100 text-green-700 hover:bg-green-200 disabled:opacity-50"
                            >
                              ACK
                            </button>
                            <button
                              onClick={() => handleNack(msg.ackId)}
                              disabled={processingAcks.includes(msg.ackId)}
                              className="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-700 hover:bg-yellow-200 disabled:opacity-50"
                            >
                              NACK
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {pulledMessages.length === 0 && (
            <div className="text-center py-8 text-gray-500 text-sm">
              No messages pulled yet. Select a subscription and click Pull.
            </div>
          )}
        </div>

        <ModalFooter>
          <ModalButton
            variant="secondary"
            onClick={() => {
              setShowPull(false);
              setPulledMessages([]);
            }}
          >
            Close
          </ModalButton>
        </ModalFooter>
      </Modal>
    </div>
  );
}
