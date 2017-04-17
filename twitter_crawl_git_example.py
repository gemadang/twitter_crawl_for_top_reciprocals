import twitter
import json
# geri madanguit
#from twitter cookbook:
def oauth_login():

    CONSUMER_KEY = ' ' #insert your own consumer key
    CONSUMER_SECRET = ' ' #insert your own consumer secret
    OAUTH_TOKEN = ' ' #insert your own oauth token
    OAUTH_TOKEN_SECRET = ' ' #insert your own oauth token secret
    auth = twitter.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET, CONSUMER_KEY, CONSUMER_SECRET)

    twitter_api = twitter.Twitter(auth=auth)
    return twitter_api

twitter_api = oauth_login()

import sys
import time
from urllib2 import URLError
from httplib import BadStatusLine

def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw):
    # A nested helper function that handles common HTTPErrors. Return an updated
    # value for wait_period if the problem is a 500 level error. Block until the
    # rate limit is reset if it's a rate limiting issue (429 error). Returns None
    # for 401 and 404 errors, which requires special handling by the caller.
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):

        if wait_period > 3600:  # Seconds
            print >> sys.stderr, 'Too many retries. Quitting.'
            raise e

        if e.e.code == 401:
            print >> sys.stderr, 'Encountered 401 Error (Not Authorized)'
            return None
        elif e.e.code == 404:
            print >> sys.stderr, 'Encountered 404 Error (Not Found)'
            return None
        elif e.e.code == 429:
            print >> sys.stderr, 'Encountered 429 Error (Rate Limit Exceeded)'
            if sleep_when_rate_limited:
                print >> sys.stderr, "Retrying in 15 minutes...ZzZ..."
                sys.stderr.flush()
                time.sleep(60 * 15 + 5)
                print >> sys.stderr, '...ZzZ...Awake now and trying again.'
                return 2
            else:
                raise e  # Caller must handle the rate limiting issue
        elif e.e.code in (500, 502, 503, 504):
            print >> sys.stderr, 'Encountered %i Error. Retrying in %i seconds' % (e.e.code, wait_period)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e

    # End of nested helper function

    wait_period = 2
    error_count = 0

    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError, e:
            error_count = 0
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError, e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print >> sys.stderr, "URLError encountered. Continuing."
            if error_count > max_errors:
                print >> sys.stderr, "Too many consecutive errors...bailing out."
                raise
        except BadStatusLine, e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print >> sys.stderr, "BadStatusLine encountered. Continuing."
            if error_count > max_errors:
                print >> sys.stderr, "Too many consecutive errors...bailing out."
                raise
# from twitter cookbook:
def get_user_profile(twitter_api, screen_names=None, user_ids=None):
    # Must have either screen_name or user_id (logical xor)
    assert(screen_names != None) != (user_ids != None), "Must have screen_names or user_ids, but not both"
    items_to_info = {}
    items = screen_names or user_ids
    while len(items) > 0:
        # Process 100 items at a time per the API specifications for /users/lookup.

        items_str = ','.join([str(item) for item in items[:100]])
        items = items[100:]
        if screen_names:
            response = make_twitter_request(twitter_api.users.lookup, screen_name=items_str)
        else: # user_ids
            response = make_twitter_request(twitter_api.users.lookup, user_id=items_str)

        for user_info in response:
            if screen_names:
                items_to_info[user_info['screen_name']] = user_info
            else:  # user_ids
                items_to_info[user_info['id']] = user_info

    return items_to_info

#print json.dumps(get_user_profile(twitter_api,user_ids=[2552962956]), indent=1)
#i started to use my sisters account: broth_baby

### Getting all friends or followers for a user
from functools import partial
from sys import maxint

def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=maxint, followers_limit=maxint):
    # Must have either screen_name or user_id (logical xor)
    assert (screen_name != None) != (user_id != None), "Must have screen_name or user_id, but not both"

    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids,
                              count=5000)
    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids,
                                count=5000)

    friends_ids, followers_ids = [], []

    for twitter_api_func, limit, ids, label in [
        [get_friends_ids, friends_limit, friends_ids, "friends"],
        [get_followers_ids, followers_limit, followers_ids, "followers"]
    ]:

        if limit == 0: continue

        cursor = -1
        while cursor != 0:

            # Use make_twitter_request via the partially bound callable...
            if screen_name:
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else:  # user_id
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']

            print >> sys.stderr, 'Fetched {0} total {1} ids for {2}'.format(len(ids),
                                                                            label, (user_id or screen_name))

            # XXX: You may want to store data during each iteration to provide an
            # an additional layer of protection from exceptional circumstances

            if len(ids) >= limit or response is None:
                break

    # Do something useful with the IDs, like store them to disk...
    return friends_ids[:friends_limit], followers_ids[:followers_limit]

#friends_ids, followers_ids = get_friends_followers_ids(twitter_api, screen_name="broth_baby", friends_limit=10, followers_limit=10)

#print friends_ids #friends = the people you follow
#print followers_ids #followers = people who follow you


#response = make_twitter_request(twitter_api.friends.ids, screen_name="broth_baby", count = 5000)
#friends = response["ids"]
#response = make_twitter_request(twitter_api.followers.ids, screen_name="broth_baby", count = 5000)
#followers = response["ids"]

#reciprocal_friends = set(friends) & set(followers) #intersection

#print reciprocal_friends

# From that list of reciprocal friends, select 5 most popular friends,
# as determined by their followers_count in their user profile.

from operator import itemgetter

##this function takes in  a set and returns a list of the top 5 (meaning 5 users with the highest follower count)
def getFive(reciprocals):
    reciprocals = list(reciprocals) #makes set = list

    val = get_user_profile(twitter_api,user_ids=[reciprocals]) #passes in userIds list and gets dictionary

    list_tuples = [(k,val[k]['followers_count']) for k in val.keys()] #iterate through dictionary

    list_of_pairs = sorted(list_tuples, key=itemgetter(1),reverse=True)
        #now we have list of tuples (id#, follower_count)
        #sorted

    top_5 = list_of_pairs[0:5] #get the first 5 in list (top 5 because sorted)

    final_5 = []
    for a,b in top_5:
        try:
            final_5.append(a) #adds to final list (not containing follower_count)
        except:
            pass
    return final_5

import networkx as nx

def crawl_followers(twitter_api, screen_name, limit, depth):
    # Resolve the ID for screen_name and start working with IDs for consistency
    # in storage

    seed_id = str(twitter_api.users.show(screen_name=screen_name)['id']) #returns id from input user name

    next_queue_friends, next_queue_follow = get_friends_followers_ids(twitter_api, user_id=seed_id,
                                              friends_limit=limit, followers_limit=limit)
    #gets friends and followers and creates a set of their intersection = reciprocal friends
    next_queue = getFive(set(next_queue_friends) & set(next_queue_follow))

    print next_queue #test print to see each ids five friends

    ls = [(seed_id,a) for a in next_queue] #adds tuples in form of graph edge notation
    social_graph.add_edges_from(ls)

    d = 1
    while d < depth:
        d += 1
        (queue, next_queue) = (next_queue, [])
        for fid in queue:

            try:
                friend_ids, follower_ids = get_friends_followers_ids(twitter_api, user_id=fid,
                                                        friends_limit=limit,
                                                        followers_limit=limit)
                ids = getFive(set(friend_ids) & set(follower_ids))
                #ids = list(set(friend_ids) & set(follower_ids))

                print ids #test print to see each ids five friends

                ls = [(fid, a) for a in ids]
                social_graph.add_edges_from(ls)
                next_queue += ids
            except:
                pass

        if(social_graph.number_of_nodes()>=100):
            break

social_graph = nx.Graph()
crawl_followers(twitter_api,'broth_baby',500,5)

#list of nodes
print social_graph.nodes()
#list of edges (tuples)
print social_graph.edges()


di = nx.diameter(social_graph)
average_dis = nx.average_shortest_path_length(social_graph)

import matplotlib.pyplot as plt

nx.draw(social_graph)
plt.savefig("top_five.png")
plt.show()

# Output data to file
output = open("prog_out_file","w")
output.write("Total number of nodes: " + str(nx.number_of_nodes(social_graph)) + "\n")
output.write("Total number of edges: " + str(nx.number_of_edges(social_graph)) + "\n")
output.write("Average length: " + str(average_dis) + "\n")
output.write("Diameter: " + str(di) + "\n")
output.close()



